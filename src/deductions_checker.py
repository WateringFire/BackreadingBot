import logging
import os
import re
import ast
import json
import time
import math
import datetime

from collections import defaultdict

from src.ed_helper import EdHelper

from typing import (
    List, Optional, Callable, Dict
)

from src.constants import (
    PROGRESS_UPDATE_MULTIPLE, NUM_PROGRESS_UPDATES
)

class DeductionsRegex:
    GENERAL_DEDUCTIONS_PATTERN = re.compile(r'.*General Deductions:\s*')
    CREATIVE_EXTENSION_PATTERN = re.compile(r'Creative Extension:\s*')
    TESTING_REFLECTION_PATTERN = re.compile(r'Testing/Reflection:.*')

class DeductionsChecker:
    @staticmethod
    async def check_deductions(
        ed_helper: EdHelper,
        urls: list[str],
        file_name: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> Dict[str, int]:
        # Get List[str] where each element is a string of one student's
        # final feedback box
        # url = ED_TESTING
        for url in urls:
        #   PIVOT TO ALL URLS PASSED IN
          feedback_list = await DeductionsChecker._pull_inlines(ed_helper, url, template, progress_bar_update, ferpa)
        # feedback_list = await DeductionsChecker._pull_submissions(ed_helper, url, template, progress_bar_update, ferpa)

        # Parse final feedback box List[str]s into a List where each
        # element is a string representation a deduction bullet point

        # Group all deduction lines into a Dict
        
        return
    
    @staticmethod
    async def _pull_inlines(
        ed_helper: EdHelper,
        url: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> List[str]:
        """
        End goal: pull all submission to get all deductions across all
        and return a map of inline title to a count of deductions. eventually
        add which assignment they were pulled from if multiple
        """
        attempt_slide = EdHelper.is_overall_submission_link(url)

        # Get the challenge id for the assignment
        ids = EdHelper.get_ids(url)
        # print(str(ids))

        #remove?
        course_id, lesson_id, slide_id = ids[0], ids[1], ids[2]

        # print(ed_helper.get_slide(url))

        challenge_id = ed_helper.get_slide(url)['challenge_id']

        attempts = ed_helper.get_attempts(lesson_id, 622271)['attempts'][0]
        # print(str((attempts)))
        # print(ed_helper.get_quiz_responses(attempts['id'], slide_id))
        # # TODO: for all the previous attempts, map the inline header "Long lines" to a list of strings ""
        # raise Exception()


        users = None
        if True:
            slide = ed_helper.get_slide(url)
            users = [user for user
                     in ed_helper.get_challenge_users(slide['challenge_id'])
                    #  if True]
                     if user['course_role'] == 'student' or user['name'] == "Colin Lim"]
        # raise Exception(users)
        # grab all submissions using their submission and challenge id
        # DEBUGGING UNCOMMENT THIS OUT RN JUST USING MY OWN
        user_ids = [user['id'] for user in users] # store user ids needed for get_challenge_submissions - challenge_id from above
        # user_ids = {622271}
        challenge_subs = [ed_helper.get_challenge_submissions(id, challenge_id) for id in user_ids ]
        submission_ids = [entry['id'] for group in challenge_subs for entry in group]

        # store all feedback in a dict (potentially need to run this on all assignments and then make a new dcit to cross reference for everything?)
        all_feedback_hopefully = {}
        all_feedback_html = ""

        # lets see how long this takes to run
        # start = time.time()

        # for every student for all student feedback, get their inline feedback and store into a file
        debugging, count = 0, 0
        inline_counts = {}
        inline_headers = [] # make a master one?

        # TODO: change to loop over when pivotign to all urls
        lesson_data = ed_helper.get_lesson(lesson_id)
        lesson_title = lesson_data['title']
        inline_counts[lesson_title] = {}
        
        for (submission_id) in submission_ids:
            # PROGRESS BAR
            if count % math.ceil(len(submission_ids) / NUM_PROGRESS_UPDATES) == 0:
                if progress_bar_update is not None:
                    _ = await progress_bar_update(count, len(submission_ids))
                logging.info(f"{count} / {len(submission_ids)} Completed")
            count = count + 1
            debugging = debugging + 1
            # if (debugging > 10):
            #     break
            
            submission_all_inlines = ed_helper.get_inline_submissions(submission_id)["comments"]
            # Skip if ungraded or no deductions
            if (submission_all_inlines is None):
                continue
            

            for full_json in submission_all_inlines:
                # Grab only the inline deductions
                inline_comment = full_json['content']
                # Take out anything after the HTML tags following the inline comment header
                remove_inline_body = re.sub(r"</.*>", "", inline_comment)
                # Grab only the inline comment header (i.e. "Quality: Long Lines")
                deduction_header = re.sub(r"<.*>", "", remove_inline_body)
                index = inline_comment.find(deduction_header) + len(deduction_header)
                # Grab only the body of the inline comment
                # TODO: figure our if want to map with this too. Currently only matching header to overall feedback
                inline_body_with_tags = inline_comment[index:]
                inline_comment_body = re.sub(r"<[^>]*>", "", inline_body_with_tags)
                
                # need to find the infomation afterwards now to add to dict
                all_feedback_hopefully[deduction_header] = inline_comment_body
                inline_headers.append(deduction_header) 
                if deduction_header not in inline_counts[lesson_title]:
                    inline_counts[lesson_title][deduction_header] = 0
                inline_counts[lesson_title][deduction_header] = inline_counts[lesson_title][deduction_header] + 1
            file_name = os.path.join("temp/", f'user-{datetime.datetime.now()}')
            with open(lesson_title, "a") as f:
                for key, value in inline_counts.items():
                    for deduct, count in value.items():
                        f.write(str(deduct) + " " + str(count) + "\n")
            # raise Exception("everything all good")
                # currently only going to match the title to the overall_feedback, can change late
        
        raise Exception()
        # print(str(inline_headers))
        # print(str(inline_counts))

        # TODO: pivot into stats?
        
        


        # end time it takes to run
        # end = time.time() 

        # with open("temp/demofile.txt", "a") as f:
        #     for key, value in inline_counts.items():
        #         for deduct, count in value.items():
        #             f.write(str(deduct) + " " + str(count) + "\n")
        # raise Exception("everything all good")

        # raise Exception(str(inline_headers))

        

    @staticmethod
    async def _pull_submissions(
        ed_helper: EdHelper,
        url: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> List[str]:
        """
        Pulls final submission slides of all student submissions and creates
        a List with all the contents of each feedback box.

        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'url' - The ed assignment url
                'template' - Whether or not the grading template is expected,
                             default False
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar, default None
                'ferpa' - Whether or not to censor student emails from links,
                          default True
        Returns: A dictionary mapping (TA | link) -> (link, fixes) for all
                 assignment that had incorrect formatting and a List of links
                 to student assignments not found in the grading spreadsheet
        """
        attempt_slide = EdHelper.is_overall_submission_link(url)

        # Get the challenge id for the assignment
        ids = EdHelper.get_ids(url)
        lesson_id, slide_id = ids[1], ids[2]
        challenge_id = (ed_helper.get_slide(url)['challenge_id']
                        if not attempt_slide else None)

        # Get user/challenge information
        users, num_criteria, rubric = None, None, None
        if not attempt_slide:
            users = [(user['id'], None, user['tutorial'], None)
                     for user in ed_helper.get_challenge_users(challenge_id)
                     if user['course_role'] == "student"]

            challenge = ed_helper.get_challenge(challenge_id)
            num_criteria = len(challenge['settings']['criteria'])
        else:
            users = [(attempt['user_id'], attempt['email'],
                      attempt['tutorial'], attempt['sourced_id'])
                     for attempt in ed_helper.get_attempt_results(lesson_id)
                     if attempt['course_role'] == 'student']

            lesson = ed_helper.get_lesson(lesson_id)
            rubric = ed_helper.get_rubric(ed_helper.get_rubric_id(slide_id))
            num_criteria = len(rubric['sections'])

        feedback_list, count = [], 0

        for (user_id, email, section, submission_id) in users:
            if count % PROGRESS_UPDATE_MULTIPLE == 0:
                if progress_bar_update is not None:
                    _ = await progress_bar_update(count, len(users))
                logging.info(f"{count} / {len(users)} Completed")
            count += 1

            submissions = (ed_helper.get_challenge_submissions(
                                user_id, challenge_id
                           ) if not attempt_slide else
                           ed_helper.get_attempt_submissions(
                                user_id, lesson_id, slide_id,
                                submission_id, rubric
                           ))
            # Get all text from final submission box
            if submissions is None:
                continue
            final_submission = submissions[0]
            if final_submission is None:
                continue
            feedback_list.append(submissions[0]['feedback']['content'])
        
        print(feedback_list)
        return feedback_list
    
    @staticmethod
    async def _get_deduction_lines(
        feedback_list: List[str]
    ) -> List[str]:
        # For creative: take everything between "General Deductions:", "Creative Extension:"
        # "Testing/Reflection:"
        deduction_lines = []
        for feedback in feedback_list:
            trim_gen_deductions = re.sub(DeductionsRegex.GENERAL_DEDUCTIONS_PATTERN, '',
                                         feedback)
            trim_creative_ext = re.sub(DeductionsRegex.CREATIVE_EXTENSION_PATTERN, '',
                                       trim_gen_deductions)
            trim_reflection = re.sub(DeductionsRegex.TESTING_REFLECTION_PATTERN, '',
                                     trim_creative_ext)
            deduction_lines.append(trim_reflection)
        
        print(deduction_lines)
        return deduction_lines
    

def _extract_comments(
    json_list: List[str]
) -> List[str]:
    """
    Extracts comments from json return 

    Args:
        json_list (List[str]): List of strings from json get call.

    Returns:
        List[str]: List of extracted paragraph texts.
    """
    comments = []
    paragraph_pattern = re.compile(r"<paragraph>(.*?)</paragraph>")

    for json in json_list:
        match = paragraph_pattern.search(json)
        if match:
            comments.append(match.group(1))

    return comments