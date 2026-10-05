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

DEBUGGING = False


class GradeCalculatorConstants:
    LETTER_GRADES = "ESNU"
    # E S U, No grade "requires" Ns, U is max U's allowed. 
    # 100 is placeholder for unlimited U's.
    MIN_GRADE_GUARANTEE = {
      'MIN_3.5': [27, 3, 0],
      'MIN_3.0': [22, 5, 0],
      'MIN_2.5': [17, 7, 0],
      'MIN_2.0': [0, 21, 100],
      'MIN_1.5': [0, 14, 100],
      'MIN_0.7': [0, 8, 100],
    }


class GradeCalculatorRegex:
    EMAIL_REGEX = re.compile(r'[A-Za-z0-9]+(@|%40)(uw|cs.washington).edu')  # noqa: E501


class GradeCalculator:
    
    @staticmethod
    async def _get_all_submissions_grades(
        ed_helper: EdHelper,
        url: str,
        user_id: str,
        student_to_grades: dict[Tuple[str,str], list[str]],
        name: str,
        email: str
    ) -> List[List[str]]:
        """
        Given a url of a final submission slide submission and a user,
        returns all of their letter grades across all submissions. 
        Params: 'ed_helper' - A properly initialized EdHelper object with API
                        access to the ed assignment
                'url' - The ed assignment to grab the grades for
                'user_id' - The student to grab grades for
                'student_to_grade' - a dict of student name/email to number of ENSU
                'name' - name matching the user_id
                'email' - email of current user_id
        Returns: A List of List of strings of all their grades in order of
                 most recent submission first going backwards.
        """
        # Should be the final submission slide viewing feedback on yourself
        course_id, lesson_id, slide_id = EdHelper.get_ids(url)

        # Get all of the attempt ids (submissions) for the given assignemnt
        attempt_ids = []
        attempt_result = ed_helper.get_attempts(lesson_id, user_id)['attempts']
        for attempt in attempt_result:
            # Staff only, if it is a dummy cannot pull grades
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
                id_to_grades[description['id']] = (ed_helper.parse_content(description['title']).strip()[0])

        # For every rubric selected item across submissions, convert to ESNU
        letter_grades = []
        for submission_grade in rubric_selected_items:
            # Ungraded, possibly an extra submission
            if (len(submission_grade) == 0):
                continue
            # Convert rubric id to letter grade
            submission_letter_grade = []
            for rubric_selected_id in submission_grade:
                submission_letter_grade.append(id_to_grades.get(rubric_selected_id))
            letter_grades.append(submission_letter_grade)

        # For all the ENSU, add to the student_to_grade dict
        if not letter_grades:
            # No grades exist
            return letter_grades
        
        # Grab the most recent grades only
        # TODO: potentially grab the previous submission if the current submission is 
        #       missing a letter grade (i.e. grading is in progress).
        for grades in letter_grades[0]:
          for letter in grades:
            index = GradeCalculatorConstants.LETTER_GRADES.find(letter)
            student_to_grades[(name,email)][index] = (
              student_to_grades[(name,email)][index] + 1
            )
            # print(student_to_grades)
        # print(letter_grades)
        return letter_grades

    @staticmethod
    async def _pull_users_and_lesson_id(
      ed_helper: EdHelper,
      url: str,
    ) -> int:
        attempt_slide = EdHelper.is_overall_submission_link(url)

        # Get the challenge id for the assignment
        ids = EdHelper.get_ids(url)
        lesson_id, slide_id = ids[1], ids[2]
        challenge_id = (ed_helper.get_slide(url)['challenge_id']
                        if not attempt_slide else None)

        users = None
        # Get user/challenge information
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
        return users, lesson_id

    @staticmethod
    async def _generate_script(
        ed_helper: EdHelper,
        urls: List[str],
        file_name: str,
        progress_bar_update: Optional[Callable[[int, int], None]] = None
    ):
        """
        Prints to {TEMP_DIR/file_name} the student name, email, and minimum grade
        guarantee based on the {MIN_GRADE_GUARANTEE} constant.
        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'urls' - The ed assignment urls
                'file_name' - What to name the resulting .csv
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar, default None
        """
        count = 0
        # Count total grades for each individual student
        student_to_grades = {} # (name, email) -> List[# E, # S, # N, # U]
        for i, url in enumerate(urls):
            users, lesson_id = await GradeCalculator._pull_users_and_lesson_id(ed_helper, url)
            
            count = 0
            for (user_id, email, section, submission_id, name) in users:
                if count % math.ceil(len(users) / NUM_PROGRESS_UPDATES) == 0:
                    if progress_bar_update is not None:
                        _ = await progress_bar_update(count, len(users))
                    logging.info(f"{count} / {len(users)} Completed")

                if (name, email) not in student_to_grades:
                    student_to_grades[(name, email)] = [0, 0, 0, 0]
                await GradeCalculator._get_all_submissions_grades(
                    ed_helper, url, user_id, student_to_grades, name, email)
            
                # TODO: pull quiz grades as well. Need to provide spreadsheets
    
            # Print completion based on ed lesson title
            lesson_data = ed_helper.get_lesson(lesson_id)
            lesson_title = lesson_data['title']
            print("Done pulling grades for lesson: " + lesson_title)
        student_min_grade = await GradeCalculator._convert_letters_to_grade(student_to_grades)

        # Format data to a list of list to be converted to csv
        csv_student_grades = []
        csv_headers = ["Name", "Email", "Grade"]
        for (name, email) in student_min_grade.keys():
          inner_csv = []
          inner_csv.append(name)
          inner_csv.append(email)
          inner_csv.append(student_min_grade.get(name,email))
          csv_student_grades.append(inner_csv)
        await GradeCalculator._create_csv(csv_student_grades, file_name, csv_headers)   

    @staticmethod
    async def _convert_letters_to_grade (
        student_to_grades: dict[Tuple[str,str], list[str]]
    ):
        """
        Given a dict student grades, calculates and returns the minimum grade guarantee
        using {MIN_GRADE_GUARANTEE}.
        Params: 'student_to_grades' - A dict of (name, email) to a list of count of ESNU grades 
        Returns: A dict of (name, email) to a String representation of their min grade (i.e. "3.0")
        """
        # (name, email) -> min numeric grade
        student_min_grade = {}
        for (name, email) in student_to_grades.keys():
            num_e = student_to_grades[(name, email)][0]
            num_s = student_to_grades[(name, email)][1]
            num_u = student_to_grades[(name, email)][3]
            for i, (min_grade, min_letters) in enumerate(GradeCalculatorConstants.MIN_GRADE_GUARANTEE.items()):
              if (num_e >= min_letters[0] and
                  (num_s + max((num_e - min_letters[0]), 0)) >= min_letters[1] and
                  num_u <= min_letters[2]):
                  student_min_grade[(name, email)] = str(min_grade[-3:])
                  break
              if (i == len(GradeCalculatorConstants.MIN_GRADE_GUARANTEE) - 1 and
                      (student_min_grade.get((name, email)) is None)):
                student_min_grade[(name, email)] = '0.0'
        print(student_min_grade)
        return student_min_grade

    
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
                'file_name' - What to name the resulting .csv
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
    ) -> Tuple[Dict[str, Tuple[str, str]], List[str], int]:
        """
        Creates a csv at {TEMP_DIR} called {file_name} mapping student
        name and email to their minimum guaranteed grade.
        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'urls' - The urls of the ed assignments to pull grades from
                'file_name' - the resulting name for the .csv
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar
        """
        if (DEBUGGING):
            await GradeCalculator._testing_conversions()

        # Remove email since it messes with ID regex
        urls = [GradeCalculatorRegex.EMAIL_REGEX.sub('', url) for url in urls]
        await GradeCalculator._generate_script(
            ed_helper, urls, file_name, progress_bar_update
        )

        if progress_bar_update:
            await progress_bar_update(1, 1)


# Manual Testing
    @staticmethod
    async def _testing_conversions():
        """
        Manual testing some borderline conversions. Throws exception if
        output does not match expected.
        """
        # Testing
        student_to_grades = {}
        #                                                   [E,S,N,U]
        student_to_grades[("BASIC: 3.5", "email@uw.edu")] = [27,3,0,0]
        student_to_grades[("BASIC: 3.0", "email@uw.edu")] = [22,5,0,0]
        student_to_grades[("BASIC: 2.5", "email@uw.edu")] = [17,7,0,0]
        student_to_grades[("BASIC: 2.0", "email@uw.edu")] = [0,21,0,0]
        student_to_grades[("BASIC: 1.5", "email@uw.edu")] = [0,14,0,0]
        student_to_grades[("BASIC: 0.7", "email@uw.edu")] = [0,8,0,0]

        student_to_grades[("COMPLEX (3.5 but 1 U): 2.0", "email@uw.edu")] = [27,3,0,1]
        student_to_grades[("COMPLEX (3.0 but 1 U): 2.0", "email@uw.edu")] = [22,5,0,1]
        student_to_grades[("COMPLEX (2.5 but 1 U): 2.0", "email@uw.edu")] = [17,7,0,1]
        student_to_grades[("COMPLEX (2.0 E/S): 2.0", "email@uw.edu")] = [20,1,0,0]

        student_to_grades[("COMPLEX (all E)): 3.5", "email@uw.edu")] = [33,0,0,0]
        student_to_grades[("COMPLEX (some N): 3.5", "email@uw.edu")] = [30,0,3,0]
        student_to_grades[("COMPLEX (all E): 3.0", "email@uw.edu")] = [27,0,3,0]
        student_to_grades[("COMPLEX (most S): 3.0", "email@uw.edu")] = [23,4,3,0]

        student_to_grades[("COMPLEX (most S): 1.5", "email@uw.edu")] = [13,1,3,10]
        student_to_grades[("COMPLEX (E/S): 0.7", "email@uw.edu")] = [1,7,0,0]
        res = await GradeCalculator._convert_letters_to_grade(student_to_grades)

        print("Actual | Expected")
        for key, value in res.items():
            simple = re.sub(r"BASIC.*:", "", key[0])
            simple = re.sub(r"COMPLEX.*:", "", simple).strip()
            print(str(simple) + " | " + str(value))
            if (str(simple) != str(value)):
                raise Exception("Wrong conversion for " + str(key[0]) + " got " + str(value))
        print("Testing complete without error. Disable {DEBUGGING} to hide.")