import os
from collections import defaultdict
from datetime import datetime, timedelta
import re
import logging
import math
import csv 
import json

from typing import (
    List, Dict, Optional, Callable, Tuple, Union
)
from src.utils import (
    write_csv, convert_csv_to_html
)
from src.constants import (
    TEMP_DIR, NUM_PROGRESS_UPDATES, LOGGING_FILE
)

from src.ed_helper import EdHelper

logging.basicConfig(filename=LOGGING_FILE, encoding='utf-8',
                    level=logging.INFO)


class MidQuarterConstants:
    OUTPUT_HEADERS = ["Name", "Section", "Email"]
    QUIZ_HEADER_LABEL = "Quiz 0"
    QUIZ_DIRECTORY = TEMP_DIR + "/Quiz_0_Version_Set_Scores.csv"
    QUIZ_GRADE_CONVERSIONS_DIRECTORY = TEMP_DIR + "/Sp26 Quiz 0 Grade Conversions - Master List.csv"


class MidQuarterRegex:
    EMAIL_REGEX = re.compile(r'[A-Za-z0-9]+(@|%40)(uw|cs.washington).edu')  # noqa: E501
    SUMMARY_FEEDBACK_REGEX = re.compile(
        r'(?=.*\bSummary\b.*)(?=.*\badditional\b.*)(?=.*\bfeedback\b.*)', re.IGNORECASE | re.DOTALL)
    QUIZ_SPREADSHEET_REGEX = r"Quiz_\d+_Version_Set_Scores.csv"


class MidQuarter:

    @staticmethod
    def _find_value_in_spreadsheet(
        file_name:str,
        target_column:str, 
        search_column:str, 
        search_value:str
    ) -> str:
        """
        Returns the value of target_column where search_column equals search_value
        from a given file_name.
        """
        with open(file_name, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get(search_column) == str(search_value):
                    return row.get(target_column)
        return ""
    
    @staticmethod
    async def _get_all_submissions_grades(
        ed_helper: EdHelper,
        url: str,
        user_id: str
    ) -> List[List[str]]:
        """
        Given a url of a final submission slide submission and a user,
        returns all of their letter grades across all submissions. 
        Params: 'ed_helper' - A properly initialized EdHelper object with API
                        access to the ed assignment
                'url' - The ed assignment to grab the grades for
                'user_id' - The student to grab grades for
        Returns: A List of List of strings of all their grades in order of
                 most recent submission first going backwards.
        """
        # Should be the final submission slide viewing feedback on yourself
        course_id, lesson_id, slide_id = EdHelper.get_ids(url)

        # Get all of the attempt ids (submissions) for the given assignemnt
        attempt_ids = []
        attempt_result = ed_helper.get_attempts(lesson_id, user_id)['attempts']
        for attempt in attempt_result:
            # Staff only, if is a dummy cannot pull grades
            if (attempt['is_dummy']):
                continue
            attempt_ids.append(attempt['id'])

        # For every attempt, grab out the selected rubric items
        # List of selected grades in order of most recent -> least recent
        rubric_selected_items = []
        for attempt_id in attempt_ids:
            quiz_responses = ed_helper.get_quiz_responses(attempt_id, slide_id)
            if (quiz_responses is None or len(quiz_responses) == 0):
                rubric_selected_items.append([])
                continue
            rubric_selected_items.append((quiz_responses)[0]['rubric_selected_items'])
        
        # Create a dict of ed internal rubric ids to single letter grades
        # will have repeat values with different keys for programming assignments
        rubric_id = ed_helper.get_rubric_id(slide_id)
        slide_rubric = (ed_helper.get_rubric(rubric_id))
        # Dict of ed internal rubric id to grade (ENSU)
        id_to_grades = {}
        num_of_grades = len(slide_rubric['sections'])
        for num_grade in range(num_of_grades):
            for description in slide_rubric['sections'][num_grade]['items']:
                # Convert "Excellent" -> "E", "Satisfactory" -> S ...
                id_to_grades[description['id']] = (ed_helper.parse_content(description['title']).strip()[0])

        # For every rubric selected item across submissions, convert to ESNU
        letter_grades = []
        for submission_grade in rubric_selected_items:
            # Ungraded, possibly an extra submission
            if (len(submission_grade) == 0):
                continue
            # Convert rubric id to letter grade
            # 
            submission_letter_grade = []
            for rubric_selected_id in submission_grade:
                # print(type(id_to_grades.keys()))
                submission_letter_grade.append(id_to_grades.get(rubric_selected_id))
            letter_grades.append(submission_letter_grade)
        return letter_grades

    @staticmethod
    async def _generate_script(
        ed_helper: EdHelper,
        urls: List[str],
        file_name: str,
        progress_bar_update: Optional[Callable[[int, int], None]] = None
    ):
        """
        Grabs all students' grades from all submissions and creates a csv
        at {file_name} with them. Will also attempt to grab quiz attendance
        from {QUIZ_DIRECTORY} and add attendance if the file exists
 
        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'urls' - The ed assignment urls
                'file_name' - Where to write the spreadsheet to
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar, default None
        """
        count, counter, all_headers = 0, 0, []
        data: dict[tuple[str, str, str], list[str]] = {}

        # Add baseline info to the csv
        for header_info in MidQuarterConstants.OUTPUT_HEADERS:
            all_headers.append(header_info)

        # Check if the quiz spreadsheet exists
        add_quiz_attendance = os.path.isfile(MidQuarterConstants.QUIZ_DIRECTORY)
        add_quiz_grades = os.path.isfile(MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY)
        print("Creating sheet with " + str(len(urls)) + " assignments.")
        if (add_quiz_grades):
            print("Quiz grades found, will be added to sheet")
        # elif (add_quiz_attendance):
        #     print("Quiz attendance found, will be added to sheet.")
        else:
            print("Quiz attendance/grades not found, if desired add file " + MidQuarterConstants.QUIZ_DIRECTORY
                    + " or " + MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY + "from Gradescope")
        for i, url in enumerate(urls):
            counter += 1

            attempt_slide = EdHelper.is_overall_submission_link(url)

            # Get the challenge id for the assignment
            ids = EdHelper.get_ids(url)
            lesson_id, slide_id = ids[1], ids[2]
            challenge_id = (ed_helper.get_slide(url)['challenge_id']
                            if not attempt_slide else None)

            # Get user/challenge information
            users = None
            if not attempt_slide:
                users = [(user['id'], None, user['tutorial'], None, None)
                        for user in ed_helper.get_challenge_users(challenge_id)
                        if user['course_role'] == "student"]
            else:
                users = [(attempt['user_id'], attempt['email'],
                        attempt['tutorial'], attempt['sourced_id'],
                        attempt['name'])
                        for attempt in ed_helper.get_attempt_results(lesson_id)
                        if attempt['course_role'] == 'student']
            
            count = 0
            for (user_id, email, section, submission_id, name) in users:

                # iywang: Progress bar update adjustments to have progress
                # bar reset for each assignment being checked and not appear
                # to stall when we have a large number of users not in the
                # spreadsheet (common for resubmissions).

                # Take ceiling to avoid mod by 0
                if count % math.ceil(len(users) / NUM_PROGRESS_UPDATES) == 0:
                    if progress_bar_update is not None:
                        _ = await progress_bar_update(count, len(users))
                    logging.info(f"{count} / {len(users)} Completed")


                # Place section and studnet email in resulting list if it doesn't exist
                if (name, section, email) not in data:
                    data[(name, section, email)] = []
                existing_grades = data[(name, section, email)]

                # Pull grades from all submissions for a student
                existing_grades.append((await MidQuarter._get_all_submissions_grades(ed_helper, url, user_id)))

                # Quiz appended grades at the end, only after the last iteration
                if (len(urls) == counter):
                    # print("Appending quiz attendance")
                    if (add_quiz_grades):
                        existing_grades.append(MidQuarter._find_value_in_spreadsheet (
                            MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY, "Q1 Decomp", "Email", email
                        ))
                        existing_grades.append(MidQuarter._find_value_in_spreadsheet (
                            MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY, "Q2 File IO", "Email", email
                        ))
                        existing_grades.append(MidQuarter._find_value_in_spreadsheet (
                            MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY, "Q3 Lookup", "Email", email
                        ))
                    elif (add_quiz_attendance):
                        existing_grades.append(MidQuarter._find_value_in_spreadsheet (
                            MidQuarterConstants.QUIZ_DIRECTORY, "Version", "Email", email
                        ))

    
            # Print completion based on ed lesson title
            lesson_data = ed_helper.get_lesson(lesson_id)
            lesson_title = lesson_data['title']
            print("Done pulling grades for lesson: " + lesson_title)

            # Create a new header for the csv based on the title
            # Find the first number in the assignment (hacky way but should work)
            assignment_number = -1
            for char in lesson_title:
                if (char.isdigit()):
                    assignment_number = char
                    break
            if ("Programming" in lesson_title):
                all_headers.append("P" + assignment_number)
            elif ("Creative" in lesson_title):
                all_headers.append("C" + assignment_number)
            else:
                all_headers.append(lesson_title)

        # Convert {data} to a simple list
        result = []
        for (name, section, email) in data.keys():
            inner_result = []
            inner_result.append(name)
            inner_result.append(section)
            inner_result.append(email)
            for v in data[(name,section,email)]:
                inner_result.append(v)
            result.append(inner_result)
        
        if add_quiz_grades:
            all_headers.append(("Quiz 0 - Q1"))
            all_headers.append(("Quiz 0 - Q2"))
            all_headers.append(("Quiz 0 - Q3"))
        elif add_quiz_attendance:
            all_headers.append((MidQuarterConstants.QUIZ_HEADER_LABEL))

        await MidQuarter._create_csv(result, file_name, all_headers)
    
    @staticmethod
    async def _create_csv(
        data: List[str],
        file_name: str,
        headers: List[str]
    ):
        """
        Given a list of elements, creates a csv at {TEMP_DIR} with all
        the provided headers and data
        Params: 'data' - A list of data to create the spreadsheet with
                'file_name' - Where to write the spreadsheet to
                'headers' - csv headers to print
        """
        file_path = os.path.join(TEMP_DIR, file_name)
        write_csv(file_path + ".csv", headers, data)

    @staticmethod
    async def create_script(
        ed_helper: EdHelper,
        urls: List[str], 
        file_name: str,
        progress_bar_update: Optional[Callable[[int, int], None]] = None
    ):
        """
        Creates a script containing a student's name, section, and email and
        all of the provided {urls} grades from all submissions. Optionally adds
        quiz attendance if the spreadsheet is provided.

        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'url' - The urls of the ed assignments to check
                'file_name' - The name to use for the two saved .csv and .html
                              files
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar
        """
        # Remove email since it messes with ID regex
        urls = [MidQuarterRegex.EMAIL_REGEX.sub('', url) for url in urls]

        # existing_grades = []
        # existing_grades.append(MidQuarter._find_value_in_spreadsheet (
        #     MidQuarterConstants.QUIZ_GRADE_CONVERSIONS_DIRECTORY, "Q3 Lookup", "Email", "daynat28@uw.edu"
        # ))
        # print(existing_grades)
        # raise Exception();

        await MidQuarter._generate_script(
            ed_helper, urls, file_name, progress_bar_update
        )

        if progress_bar_update:
            await progress_bar_update(1, 1)
