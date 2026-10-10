"""
CampusLens - Seed Data Generator
Populates realistic sample campus notices and tasks for immediate demo & UI testing.
"""

from datetime import date, timedelta
from task_manager import task_manager

def populate_seed_data():
    today = date.today()
    d_plus_2 = (today + timedelta(days=2)).isoformat()
    d_plus_4 = (today + timedelta(days=4)).isoformat()
    d_plus_7 = (today + timedelta(days=7)).isoformat()
    d_plus_10 = (today + timedelta(days=10)).isoformat()

    sample_notices = [
        {
            "title": "OpenLake × MLH Build with Gemma 4 Hackathon Submission",
            "category": "Hackathon",
            "issuer": "OpenLake & Google Developer Student Club",
            "issue_date": today.isoformat(),
            "deadline": d_plus_2,
            "venue": "CC-302 Computer Lab & Organizer Portal",
            "eligibility": "All registered undergraduate and postgraduate teams",
            "summary": "Final project code, public GitHub repository, Agent Skill file, and demo presentation must be submitted before deadline.",
            "action_items": [
                "Push code and LICENSE to public GitHub repository",
                "Add Agent Skill file (SKILL.md) and specify gemma-4-26b-a4b-it",
                "Submit project link on Organizer HQ portal"
            ]
        },
        {
            "title": "Monthly Hostel Mess Rebate Application - Oct Cycle",
            "category": "Hostel",
            "issuer": "Council of Wardens (CoW)",
            "issue_date": today.isoformat(),
            "deadline": d_plus_4,
            "venue": "Hall of Residence 1 Office & Student ERP Portal",
            "eligibility": "Hostel residents away for > 4 consecutive days with leave approval",
            "summary": "Mess rebate claims must be filed within 5 days of returning. Attach signed warden permission slip.",
            "action_items": [
                "Download rebate claim form from ERP portal",
                "Get caretaker signature and submit to Mess Supervisor"
            ]
        },
        {
            "title": "Autumn Semester Mid-Term Examination Hall Ticket & Schedule",
            "category": "Examination",
            "issuer": "Academic Affairs Office",
            "issue_date": today.isoformat(),
            "deadline": d_plus_7,
            "venue": "Academic Block A - Examination Halls 1 to 4",
            "eligibility": "Students with >= 75% minimum attendance in all registered courses",
            "summary": "Hall tickets are available on the AIMS portal. Physical printouts signed by Faculty Advisor are mandatory for exam entry.",
            "action_items": [
                "Download and print hall ticket from AIMS portal",
                "Obtain Faculty Advisor signature before Friday"
            ]
        },
        {
            "title": "Central Library Book Return & Clearance Notice",
            "category": "Academic",
            "issuer": "Central Library Services",
            "issue_date": today.isoformat(),
            "deadline": d_plus_10,
            "venue": "Central Library Circulation Counter",
            "eligibility": "All registered student library card holders",
            "summary": "Renew or return overdue books before the fine waiver deadline to maintain uninterrupted digital catalog access.",
            "action_items": [
                "Check issued books on library portal",
                "Return overdue books or renew online"
            ]
        }
    ]

    print("Populating CampusLens seed data...")
    for notice in sample_notices:
        success, msg, saved = task_manager.ingest_extracted_notice(notice)
        print(f"[{'OK' if success else 'FAIL'}] {notice['title']} -> {msg}")

    stats = task_manager.get_dashboard_summary()
    print("\nCampusLens Demo Store Ready!")
    print(f"Total Notices: {stats['total_notices']}")
    print(f"Total Tasks: {stats['total_tasks']}")
    print(f"Upcoming Deadlines: {stats['upcoming_deadlines_count']}")

if __name__ == "__main__":
    populate_seed_data()
