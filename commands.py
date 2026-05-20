import os
import asyncio
import re
import argparse
import datetime
import zoneinfo

from src.ed_helper import EdHelper
from src.consistency_checker import ConsistencyChecker
from src.midquarter import MidQuarter
from src.grade_calculator import GradeCalculator
from src.deductions_checker import DeductionsChecker
from src.consistency_resub_checker import ConsistencyResubChecker
from src.utils import (
    progress_bar, invert_csv
)
from src.exceptions import (
    MissingArgument, InvalidArgument
)
from src.constants import (
    TEMP_DIR, TIMEZONE_REGION_NAME
)

CHOICES = ['consistency', 'consistency_resub', 'ungraded', 'check_feedback_boxes', 'midquarter', 'grade_calculator', 'deductions']
PROGRESS_INCREMENT = 50


async def main():
    for choice in CHOICES:
        if choice not in globals() or not callable(globals()[choice]):
            raise Exception(f"Not a function with matching name: {choice}")

    parser = argparse.ArgumentParser(
        description="This script library allows CSE 12x/14x TAs perform " +
                    "various grading assistance checks"
    )
    parser.add_argument(
        '--command', '-c',
        help='What command would you like to run',
        choices=CHOICES, required=True
    )
    parser.add_argument(
        '--ed_token', '-e',
        help='Ed API token to make requests with'
    )
    parser.add_argument(
        '--assignment_config_file', '-a',
        help="Path to configuration file containing all assignment " +
             "final submission slide links"
    )
    parser.set_defaults(assignment_config_file=None)
    parser.add_argument(
        '--assignment_nums', '-n',
        nargs='+',
        help="Row numbers of configuration file whose links to use"
    )
    parser.set_defaults(assignment_nums=None)
    parser.add_argument(
        '--assignment_link', '-l',
        nargs='+',
        help="Assignment link(s) you'd like to check, should link to the Final " +
             "Submission slide"
    )
    parser.add_argument(
        '--scrubbed_spreadsheet', '-s',
        nargs='+',
        help="Path(s) to the scrubbed grading spreadsheet(s); should correspond " +
             "one-to-one with assignment links"
    )
    parser.add_argument(
        '--template', '-t',
        help="Enables checking against the overall feedback template",
        dest='template', action='store_true'
    )
    parser.set_defaults(template=False)
    parser.add_argument(
        '--ferpa', '-f',
        help="Enables FERPA mode, removing student emails from results",
        dest='ferpa', action='store_true'
    )
    parser.set_defaults(ferpa=False)
    parser.add_argument(
        '--query', '-q',
        help="Search query term"
    )
    parser.set_defaults(resub_due=None)
    parser.add_argument(
        '--resub_due', '-d',
        help="Resub due date"
    )

    args = parser.parse_args()
    await globals()[args.command](args)

async def deductions(args):
    # TODO: grab token from auth.json is tag is not there?
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    # if args.assignment_link is None:
    #     raise MissingArgument("Assignment link required to run grading checks")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")
    # if not EdHelper.valid_assignment_url(args.assignment_link):
    #     raise InvalidArgument("Assignment link is invalid")

    # Check links file exists and matches number of links
    if args.assignment_nums:
        if args.assignment_config_file is None:
            raise MissingArgument("Assignment link file (--assignment_config_file [file_name])"
                                  " required to use row numbers!")
        
        num_assignments = sum(1 for line in open(args.assignment_config_file))
        for num in args.assignment_nums:
            if int(num) <= 0 or int(num) > num_assignments:
                raise InvalidArgument(f"Assignment number {num} not in assignment link file")

        config_file = open(args.assignment_config_file)

        assignment_links = []
        for i, line in enumerate(config_file):
            if str(i + 1) in args.assignment_nums:
                assignment_links.append(line.strip())
    # Ohterwise, invalid
    else:
        raise MissingArgument("Missing assignment number (--assignment_num [num]) required to run grading checks!")
    
    # Validate all Ed assignment links
    for assignment_link in assignment_links:
        if not EdHelper.valid_assignment_url(assignment_link):
            raise InvalidArgument(f"Assignment link is invalid: {assignment_link}")


    ed_helper = EdHelper(args.ed_token)
    file_name = os.path.join(TEMP_DIR, f'user-{datetime.datetime.now()}')

    print("\nRunning deductions checker:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)

    grouped_deductions = (
        await DeductionsChecker.check_deductions(
            ed_helper, assignment_links, file_name, args.template,
            update_progress, args.ferpa
        )
    )

async def grade_calculator(args):
    # Check and validate ed token (-e {ED_TOKEN})
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")

    # Check links file exists and links are valid (-a {link_directory})
    if args.assignment_config_file is None:
        raise MissingArgument("Assignment link file (--assignment_config_file [file_name])"
                                " required to use row numbers!")
    config_file = open(args.assignment_config_file)
    assignment_links = []
    num_lines = sum(1 for _ in open(args.assignment_config_file))
    for i, line in enumerate(config_file):
        if str(i + 1) in range(num_lines):
            assignment_links.append(line.strip())
    # Validate all Ed assignment links
    for assignment_link in assignment_links:
        if not EdHelper.valid_assignment_url(assignment_link):
            raise InvalidArgument(f"Assignment link is invalid: {assignment_link}")


    ed_helper = EdHelper(args.ed_token)
    file_name = os.path.join(TEMP_DIR, f'user-{datetime.datetime.now()}')

    print("\nRunning grade calculator:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)
    
    await GradeCalculator.create_script(
        ed_helper, assignment_links, file_name,
        update_progress
    )
    print()
    print("Result files can be found at:" +
          f"\n\t{file_name}.csv\n\t{file_name}.html\n")

async def midquarter(args):
    # Valid Ed token ALWAYS required to run consistency checks
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")

    # Option 1: args contain assignment number(s) AND assignment link file
    # (note: assignment number takes precedence over explicit link(s))
    if args.assignment_nums:
        if args.assignment_config_file is None:
            raise MissingArgument("Assignment link file (--assignment_config_file [file_name])"
                                  " required to use row numbers!")
        
        num_assignments = sum(1 for line in open(args.assignment_config_file))
        for num in args.assignment_nums:
            if int(num) <= 0 or int(num) > num_assignments:
                raise InvalidArgument(f"Assignment number {num} not in assignment link file")

        config_file = open(args.assignment_config_file)

        assignment_links = []
        for i, line in enumerate(config_file):
            if str(i + 1) in args.assignment_nums:
                assignment_links.append(line.strip())
    # Option 2: args contain assignment link(s) explicitly
    elif args.assignment_link:
        assignment_links = args.assignment_link
    # Ohterwise, invalid
    else:
        raise MissingArgument("Either assignment link (--assignment_link [link]) or assignment"
                              " number (--assignment_num [num]) required to run grading checks!")
    
    # Validate all Ed assignment links
    for assignment_link in assignment_links:
        if not EdHelper.valid_assignment_url(assignment_link):
            raise InvalidArgument(f"Assignment link is invalid: {assignment_link}")

    ed_helper = EdHelper(args.ed_token)
    file_name = os.path.join(TEMP_DIR, f'user-{datetime.datetime.now()}')

    print("\nRunning midquarter script generator:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)
    
    await MidQuarter.create_script(
        ed_helper, assignment_links, file_name,
        update_progress
    )
    print()
    print("Result files can be found at:" +
          f"\n\t{file_name}.csv")


async def consistency(args):
    # Valid Ed token ALWAYS required to run consistency checks
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")

    # Option 1: args contain assignment number AND assignment link file
    # (note: assignment number takes precedence over explicit link)
    if args.assignment_nums is not None:
        if args.assignment_config_file is None:
            raise MissingArgument("Assignment link file (--assignment_config_file [file_name]) required"
                                  " to use row numbers!")
        
        if len(args.assignment_nums) > 1:
            print("NOTE: Only the first assignment number is used for regular grading checks!")
        
        config_file = open(args.assignment_config_file)
        try:
            assignment_row_num = int(args.assignment_nums[0]) - 1
        except:
            raise InvalidArgument("Row number " + args.assignment_nums[0] + " is not an integer!")

        assignment_link = config_file.readlines()[assignment_row_num].strip()
    # Option 2: args contain assignment link explicitly
    elif args.assignment_link is not None:
        if len(args.assignment_link) > 1:
            print("NOTE: Only the first assignment link is used for regular grading checks!")
        
        assignment_link = args.assignment_link[0]
    # Ohterwise, invalid
    else:
        raise MissingArgument("Either assignment link (--assignment_link [link]) or assignment number"
                              " (--assignment_num [num]) required to run grading checks!")
    
    # Validate Ed assignment link
    if not EdHelper.valid_assignment_url(assignment_link):
        raise InvalidArgument(f"Assignment link is invalid: {assignment_link}")

    spreadsheet = None
    if args.scrubbed_spreadsheet:
        spreadsheet = invert_csv(open(args.scrubbed_spreadsheet[0]).read())

    ed_helper = EdHelper(args.ed_token)
    file_name = os.path.join(TEMP_DIR, f'user-{datetime.datetime.now()}')

    print("\nRunning consistency checker:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)

    fixes, not_present, total_issues = (
        await ConsistencyChecker.check_consistency(
            ed_helper, assignment_link, file_name, args.template,
            spreadsheet, update_progress, args.ferpa
        )
    )

    print()
    print("All clear!" if total_issues == 0 else
          f"{total_issues} students with consistency issues")
    if total_issues > 0:
        print("Found Issues:")
        for ta, issues in fixes.items():
            print(f"\t{'TA' if spreadsheet is not None else 'Section'}: " +
                  f"{ta}, Issues: {len(issues)}")
            for issue in issues:
                print(f"\t\t{issue}")
    if len(not_present) > 0:
        print()
        print("Student submissions not present in grading spreadsheet: "
              f"({len(not_present)})")
        for link in not_present:
            print(f"\t{link}")
    print()
    print("Result files can be found at:" +
          f"\n\t{file_name}.csv\n\t{file_name}.html\n")

async def consistency_resub(args):
    # Valid Ed token ALWAYS required to run consistency checks
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")

    if args.resub_due is None:
        raise MissingArgument("Resub due date (--resub_due [MM/DD/YY HH:MM:SS])"
                              " required to run resub consistency checks")

    # Option 1: args contain assignment number(s) AND assignment link file
    # (note: assignment number takes precedence over explicit link(s))
    if args.assignment_nums:
        if args.assignment_config_file is None:
            raise MissingArgument("Assignment link file (--assignment_config_file [file_name])"
                                  " required to use row numbers!")
        
        num_assignments = sum(1 for line in open(args.assignment_config_file))
        for num in args.assignment_nums:
            if int(num) <= 0 or int(num) > num_assignments:
                raise InvalidArgument(f"Assignment number {num} not in assignment link file")

        config_file = open(args.assignment_config_file)

        assignment_links = []
        for i, line in enumerate(config_file):
            if str(i + 1) in args.assignment_nums:
                assignment_links.append(line.strip())
    # Option 2: args contain assignment link(s) explicitly
    elif args.assignment_link:
        assignment_links = args.assignment_link
    # Ohterwise, invalid
    else:
        raise MissingArgument("Either assignment link (--assignment_link [link]) or assignment"
                              " number (--assignment_num [num]) required to run grading checks!")
    
    # Validate all Ed assignment links
    for assignment_link in assignment_links:
        if not EdHelper.valid_assignment_url(assignment_link):
            raise InvalidArgument(f"Assignment link is invalid: {assignment_link}")

    spreadsheets = None
    # Check correct number of spreadsheets, if applicable
    if args.scrubbed_spreadsheet:
        if len(assignment_links) != len(args.scrubbed_spreadsheet):
            raise InvalidArgument("Must have same number of assignment links and"
                                  " scrubbed spreadsheets")
        
        spreadsheets = [None] * len(args.scrubbed_spreadsheet)
        for i, scrubbed_spreadsheet in enumerate(args.scrubbed_spreadsheet):
            spreadsheets[i] = invert_csv(open(scrubbed_spreadsheet).read())

    ed_helper = EdHelper(args.ed_token)
    file_name = os.path.join(TEMP_DIR, f'user-{datetime.datetime.now()}')

    print("\nRunning resub consistency checker:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)
    
    # Convert timezone-naive string into timezone-aware datetime
    resub_due = datetime.datetime.strptime(
        args.resub_due,
        '%m/%d/%y %H:%M:%S'
    ).replace(tzinfo=zoneinfo.ZoneInfo(TIMEZONE_REGION_NAME))

    fixes, not_present, total_issues = (
        await ConsistencyResubChecker.check_consistency(
            ed_helper, assignment_links, file_name, resub_due,
            args.template, spreadsheets, update_progress, args.ferpa
        )
    )

    print()
    print("All clear!" if total_issues == 0 else
          f"{total_issues} students with consistency issues")
    if total_issues > 0:
        print("Found Issues:")
        for ta, issues in fixes.items():
            print(f"\t{'TA' if spreadsheets is not None else 'Section'}: " +
                  f"{ta}, Issues: {len(issues)}")
            for issue in issues:
                print(f"\t\t{issue}")
    if len(not_present) > 0:
        print()
        print("Student submissions not present in grading spreadsheet: "
              f"({len(not_present)})")
        for link in not_present:
            print(f"\t{link}")
    print()
    print("Result files can be found at:" +
          f"\n\t{file_name}.csv\n\t{file_name}.html\n")

async def ungraded(args):
    if args.ed_token is None:
        raise MissingArgument("Ed token required to run grading checks")
    if args.assignment_link is None:
        raise MissingArgument("Assignment link required to run grading checks")
    assignment_link = args.assignment_link[0]
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")
    if not EdHelper.valid_assignment_url(assignment_link):
        raise InvalidArgument("Assignment link is invalid")

    spreadsheet = None
    if args.scrubbed_spreadsheet is not None:
        spreadsheet = open(args.scrubbed_spreadsheet[0])

    ed_helper = EdHelper(args.ed_token)
    print("\nRunning grade completion checker:")
    print(progress_bar(0, 1), end='\r', flush=True)

    async def update_progress(curr, total):
        print(progress_bar(curr, total), end='\n' if curr == total
              else '\r', flush=True)

    key_to_ungraded, not_present, total_ungraded = (
        await ConsistencyChecker.check_ungraded(
            ed_helper, assignment_link, spreadsheet, update_progress
        )
    )

    print("All clear!" if total_ungraded == 0
          else f"{total_ungraded} students with incomplete grading")
    if total_ungraded > 0:
        print("Found Ungraded Instances:")
        for ta, ungraded in key_to_ungraded.items():
            print(f"\t{'TA' if spreadsheet is not None else 'Section'}: " +
                  "{ta}, Ungraded: {ungraded}")
    if not_present > 0:
        print()
        print("Total student submissions not present in grading " +
              f"spreadsheet: {not_present}")
        print("Refresh grading roster!")
    print()


async def check_feedback_boxes(args):
    if args.ed_token is None:
        raise MissingArgument("Ed token required to check feedback boxes")
    if args.assignment_link is None:
        raise MissingArgument("Assignment link required to check feedback " +
                              "boxes")
    assignment_link = args.assignment_link[0]
    if args.query is None:
        raise MissingArgument("Query to search for required when checking " +
                              "feedback boxes")
    if not EdHelper.valid_token(args.ed_token):
        raise InvalidArgument("Ed token is invalid")
    if not EdHelper.valid_assignment_url(assignment_link):
        raise InvalidArgument("Assignment link is invalid")

    args.query = args.query.lower()
    ed_helper = EdHelper(args.ed_token)
    ids = EdHelper.get_ids(assignment_link)
    results = ed_helper.get_attempt_results(ids[1])

    print()
    print(f"Running check for: {assignment_link}")
    print(progress_bar(0, 1), end='\r', flush=True)
    found, i = [], 0
    for result in results:
        if i % PROGRESS_INCREMENT == 0:
            print(progress_bar(i, len(results)), end='\r', flush=True)
        i += 1

        user_id = result['user_id']
        email = result['email']
        attempt_id = ed_helper.get_attempts(ids[1], user_id)['final_id']
        response = ed_helper.get_quiz_responses(attempt_id, ids[2])[0]

        if (response is not None and
                response['lesson_mark'] is not None and
                response['lesson_mark']['comment'] is not None):
            if re.search(args.query,
                         response['lesson_mark']['comment'].lower()):
                found.append(ConsistencyChecker._get_link(
                    ids, user_id, email, None, True, False
                ))

    print(progress_bar(1, 1), end='\r', flush=True)
    print()
    print(f"Found students with query '{args.query}':")
    for link in found:
        print(f"\t{link}")
    print()
    print(f"Total number of occurrences found: {len(found)}")


if __name__ == "__main__":
    asyncio.run(main())
