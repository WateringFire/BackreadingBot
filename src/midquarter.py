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
    TEMP_DIR, NUM_PROGRESS_UPDATES, PROGRESS_UPDATE_MULTIPLE, RESUB_GRACE_MINUTES, LOGGING_FILE
)

from src.ed_helper import EdHelper

logging.basicConfig(filename=LOGGING_FILE, encoding='utf-8',
                    level=logging.INFO)


class ConsistencyResubConstants:
    FEEDBACK_BOX_REGEX = r'({criteria_name})[a-zA-Z\s]*:\s*_*(\({criteria_mark}\)|{criteria_mark})'  # noqa: E501
    TEMPLATE_REGEX = r'({criteria_name})[a-zA-Z\s\\/]*:'  # noqa: E501
    VIEW_SUBMISSION_LINK = 'https://edstem.org/us/courses/{course_id}/lessons/{lesson_id}/slides/{slide_id}/submissions?u={user_id}&s={submission_id}'  # noqa: E501
    FERPA_VIEW_ATTEMPT_LINK = 'https://edstem.org/us/courses/{course_id}/lessons/{lesson_id}/attempts?slide={slide_id}&s={submission_id}'  # noqa: E501
    VIEW_ATTEMPT_LINK = 'https://edstem.org/us/courses/{course_id}/lessons/{lesson_id}/attempts?slide={slide_id}&email={email}'  # noqa: E501
    ASSIGNMENT_ORDER = ["C0", "P0", "C1", "P1", "P2"]
    QUIZ_LABEL = "Quiz 0"


class MidQuarterRegex:
    EMAIL_REGEX = re.compile(r'[A-Za-z0-9]+(@|%40)(uw|cs.washington).edu')  # noqa: E501
    SUMMARY_FEEDBACK_REGEX = re.compile(
        r'(?=.*\bSummary\b.*)(?=.*\badditional\b.*)(?=.*\bfeedback\b.*)', re.IGNORECASE | re.DOTALL)
    QUIZ_SPREADSHEET_REGEX = r"Quiz_\d+_Version_Set_Scores.csv"


class MidQuarter:
    @staticmethod
    def _parse_overall(
        all_criteria: List[Dict],
    ) -> str:
        """
        Returns all grades from this assignments as a list

        Params: 'all_criteria' - Ed criteria dropdown objects
        Returns: A List containing just the letter grade times however rubric items.
        """
        result = []
        for criteria in all_criteria:
            result.append(criteria['mark'])
        return result
                    

    def _check_quiz_spreadsheet(
        filepath:str,
        target_column:str, 
        search_column:str, 
        search_value:str
    ) -> str:
        """
        Returns the value of target_column where search_column equals search_value.
        """
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get(search_column) == str(search_value):
                    if row.get(target_column) == "Missing":
                        return "Missing"
        return ""


    @staticmethod
    def _find_submission_fixes(
        submissions: List[Dict],
        ids: List[int],
        user_id: int,
        email: str,
        section: str,
        file_name: str
    ) -> Tuple[str, int]:
        """
        Parses through a students graded submissions and reports any issues
        found with grading formatting

        Params: 'submissions' - A list of Ed submission objects
                'num_criteria' - The total number of criteria that need to be
                                 filled out
                'due_at' - A datetime object representing the due date of the
                           assignment
                'template' - Whether or not the grading template is expected
        Returns: Tuple where string is submission grade(s), int is number of graded submissions
                 (resubmissions)
        """
        submission_nums = 0 
        data = []
        # print("new loop")
        # print (submissions)
        # TODO GET ALL FEEDBACK FROM THIS LINE AND COUNT RESUBS
        print("new submission --------------- with length: " + str(len(submissions)))
        for submission in submissions:
            if (submission['feedback'] is not None):
                print("feedback is " + str(submission['feedback']))
                print(submission['feedback']['criteria'])
            else:
                print("feedback is none")
            
            if (submission['feedback'] is not None and submission['feedback']['criteria'] != ''):
                submission_nums += 1
                # print(submission['id'])
                # print(email + " " + section)
                submission_info = []
                submission_str = ''
                # submission_info.append(section)
                # submission_info.append(email)

                # submission_info.append(MidQuarter._parse_overall(submission['feedback']['criteria']))
                submission_str = (MidQuarter._parse_overall(submission['feedback']['criteria']))
                # for (i) in range()
                # data.append(submission_info)
                if (len(submissions) > 1):
                    Exception("MORE THAN ONE SUB CHANGE IMPL")
                return submission_str
            elif (submission['feedback']['criteria']):
                submission_nums += 1
        return data
        
        # for submission in submissions:
        #     created_at = EdHelper.parse_datetime(submission['created_at'])
        #     grace_period = timedelta(minutes=RESUB_GRACE_MINUTES)

        #     if created_at < due_at + grace_period:
        #         if submission['feedback'] is not None and (submission['feedback']['criteria'] != [] or submission['feedback']['content'] != ''):
        #             reason = "Possible late submission graded, "
        #             content = EdHelper.parse_content(
        #                 submission['feedback']['content']
        #             )
        #             if len(submission['feedback']['criteria']) != num_criteria:
        #                 # if MidQuarterRegex.SUMMARY_FEEDBACK_REGEX.search(content):
        #                 #     reason += "Re-resub, " # To count how many re-resubs there were!

        #                 # This is a check that factors out the re-resubs given out. Since re-resubs aren't
        #                 # assigned any grades, we don't want to output any of them since the output gets very noisy then.
        #                 if not MidQuarterRegex.SUMMARY_FEEDBACK_REGEX.search(content):
        #                     reason += "Not all dimensions assigned a grade, "
        #             if not MidQuarterRegex.EMAIL_REGEX.search(content):
        #                 # Missing contact info email
        #                 reason += "Missing or incorrect TA contact information, "
        #             if template:
        #                 # Lets check to see if a template is being used - assuming
        #                 # the format is "Dimension: Score"
        #                 reason += MidQuarter._check_criteria(
        #                     submission['feedback']['criteria'], content
        #                 )
        #             if reason != "":
        #                 return reason[:-2], submission['id']
        #     else:
        #         if submission['feedback'] is None:
        #             # Feedback not given to appropriate submission
        #             return ("Missing grade / incorrect submission graded or " +
        #                     "marked final", submission['id'])
                
        #         reason = ""
        #         content = EdHelper.parse_content(
        #             submission['feedback']['content']
        #         )
        #         if len(submission['feedback']['criteria']) != num_criteria:
        #             # if MidQuarterRegex.SUMMARY_FEEDBACK_REGEX.search(content):
        #             #     reason += "Re-resub, "

        #             # This is a check that factors out the re-resubs given out. Since re-resubs aren't
        #             # assigned any grades, we don't want to output any of them since the output gets very noisy then.
        #             if not MidQuarterRegex.SUMMARY_FEEDBACK_REGEX.search(content):
        #                 reason += "Not all dimensions assigned a grade, "
        #         if not MidQuarterRegex.EMAIL_REGEX.search(content):
        #             # Missing contact info email
        #             reason += "Missing TA contact information, "
        #         if template:
        #             # Lets check to see if a template is being used - assuming
        #             # the format is "Dimension: Score"
        #             reason += MidQuarter._check_criteria(
        #                 submission['feedback']['criteria'], content
        #             )
        #         if reason != "":
        #             return reason[:-2], submission['id']
        #         break
        return None, None

        
    @staticmethod
    async def _get_all_submissions_grades(
        ed_helper: EdHelper,
        url: str,
        user_id: str
    ):
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
        # print("All selected rubric items " + str(rubric_selected_items))
        
        # Create a dict of ed internal rubric ids to single letter grades
        # will have repeat values, with different keys for programming assignments
        rubric_id = ed_helper.get_rubric_id(slide_id)
        slide_rubric = (ed_helper.get_rubric(rubric_id))
        # Dict of ed internal rubric id to grade (ENSU)
        id_to_grades = {}
        num_of_grades = len(slide_rubric['sections'])
        for num_grade in range(num_of_grades):
            for description in slide_rubric['sections'][num_grade]['items']:
                # Convert "Excellent" -> "E", "Satisfactory" -> S ...
                id_to_grades[description['id']] = (ed_helper.parse_content(description['title']).strip()[0])
        # print("Id to grade dict " + str(id_to_grades))

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
        # print("All submissions, all letter grades " + str(letter_grades))
        return letter_grades

    @staticmethod
    async def _find_fixes(
        ed_helper: EdHelper,
        urls: List[str],
        file_name: str,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True,
    ) -> Tuple[Dict[str, List[Tuple[str, str]]], List[str]]:
        """
        Finds all student submissions that have inconsistently formatted
        grading feedback and creates a dictionary containing the fixes that
        need to be made before publishing grades

        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'urls' - The ed assignment urls
                'resub_due' - The resubmission due date to enforce in place of
                              the assignment due date
                'template' - Whether or not the grading template is expected,
                             default False
                'spreadsheet' - A list of dictionaries mapping ed student ID to TA name,
                                default None
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar, default None
                'ferpa' - Whether or not to censor student emails from links,
                          default True
        Returns: A dictionary mapping (TA | link) -> (link, fixes) for all
                 assignment that had incorrect formatting and a List of links
                 to student assignments not found in the grading spreadsheet
        """
        fixes, not_present, count = defaultdict(list), [], 0
        data: dict[tuple[str, str], list[str]] = {}
        counter = 0
        for i, url in enumerate(urls):
            counter += 1
            spreadsheet = None
            # if spreadsheets:
            #     spreadsheet = spreadsheets[i]

            attempt_slide = EdHelper.is_overall_submission_link(url)

            # Get the challenge id for the assignment
            ids = EdHelper.get_ids(url)
            lesson_id, slide_id = ids[1], ids[2]
            challenge_id = (ed_helper.get_slide(url)['challenge_id']
                            if not attempt_slide else None)

            # Get user/challenge information
            users, due_at, num_criteria, rubric = None, None, None, None
            if not attempt_slide:
                users = [(user['id'], None, user['tutorial'], None)
                        for user in ed_helper.get_challenge_users(challenge_id)
                        if user['course_role'] == "student"]

                challenge = ed_helper.get_challenge(challenge_id)
                due_at = EdHelper.parse_datetime(challenge['due_at'],
                                                milliseconds=False)
                num_criteria = len(challenge['settings']['criteria'])
            else:
                users = [(attempt['user_id'], attempt['email'],
                        attempt['tutorial'], attempt['sourced_id'])
                        for attempt in ed_helper.get_attempt_results(lesson_id)
                        if attempt['course_role'] == 'student']

                lesson = ed_helper.get_lesson(lesson_id)
                due_at = EdHelper.parse_datetime(lesson['due_at'],
                                                milliseconds=False)
                rubric = ed_helper.get_rubric(ed_helper.get_rubric_id(slide_id))
                num_criteria = len(rubric['sections'])

            not_present, count = [], 0
            for (user_id, email, section, submission_id) in users:
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
                if (section,email) not in data:
                    data[(section,email)] = []
                existing_grades = data[(section, email)]

                # Pull grades from all submissions for a student
                print("Grabbing grades for student: " + email)
                existing_grades.append((await MidQuarter._get_all_submissions_grades(ed_helper, url, user_id)))

                # quiz grades at the end, only after the last iteration
                if (len(urls) == counter):
                    print("Appending quiz attendance")
                    existing_grades.append(MidQuarter._check_quiz_spreadsheet (
                        "temp/Quiz_0_Version_Set_Scores.csv", "Version", "Email", email
                    ))
            lesson_data = ed_helper.get_lesson(lesson_id)
            print("Done pulling grades for lesson: " + lesson_data['title'])


        
        result = []
        for (k1, k2) in data.keys():
            inner_result = []
            inner_result.append(k1)
            inner_result.append(k2)
            for v in data[(k1,k2)]:
                inner_result.append(v)
            result.append(inner_result)
        file_path = os.path.join(TEMP_DIR, file_name)
        # TODO add a flag if quiz is included
        quiz_flag = True
        output_headers = ["Section", "Email"]
        for (i) in range(len(urls)):
            output_headers.append(ConsistencyResubConstants.ASSIGNMENT_ORDER[i])
        if (quiz_flag):
            output_headers.append(ConsistencyResubConstants.QUIZ_LABEL)
        write_csv(file_path + ".csv", output_headers, result)
        logging.info("Completed consistency check")
        return fixes, not_present

    @staticmethod
    def _convert_fixes_to_list(
        fixes: Dict[str, Tuple[str, str]]
    ) -> List[List[str]]:
        """
        Converts the fixes dictionary to a list format used to export .csv and
        .html files

        Params: 'fixes' - A dictionary mapping (TA | link) -> (link, issue)
        Returns: A list of [(TA | link), link, issue] lists
        """
        data = []
        for ta, issues in fixes.items():
            for (link, issue) in issues:
                data.append([ta, link, issue])
        return data

    @staticmethod
    async def check_consistency(
        ed_helper: EdHelper,
        urls: List[str], 
        file_name: str,
        progress_bar_update: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[Dict[str, Tuple[str, str]], List[str], int]:
        """
        Checks and organizes information regarding grading consistency for a
        given ed assignment.

        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'url' - The urls of the ed assignments to check
                'file_name' - The name to use for the two saved .csv and .html
                              files
                'spreadsheet' - A list of dictionaries mapping ed student ID to TA name
                                (can be None)
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar
                'ferpa' - Whether or not to censor student emails from links,
                          default True
        Returns: A dictionary mapping (TA | link) -> (link, fixes) for all
                 assignment that had incorrect formatting, a list of links to
                 student assignments not found in the grading spreadsheet, and
                 the total number of issues found
        """
        # iywang: Since multiple assignments are typically eligible per resub
        # cycle, allow for multiple assignments to be consistency-checked
        # at a time under one resub due date. Also, no longer hard-coding
        # resub due date (must pass in from cmd line).

        # Remove email since it messes with ID regex
        urls = [MidQuarterRegex.EMAIL_REGEX.sub('', url) for url in urls]

        fixes, not_present = (
            await MidQuarter._find_fixes(
                ed_helper, urls, file_name, progress_bar_update, True
            )
        )
        if progress_bar_update:
            await progress_bar_update(1, 1)

        # # Write the info into files to be sent
        # data = MidQuarter._convert_fixes_to_list(fixes)
        # total_issues = len(data)

        # file_path = os.path.join(TEMP_DIR, file_name)
        # write_csv(file_path + ".csv", ['TA', 'Link', 'Issue'], data)
        # # convert_csv_to_html(file_path + ".csv", file_path + ".html")

        return fixes, not_present, 0
