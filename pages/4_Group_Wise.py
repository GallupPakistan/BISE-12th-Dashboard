"""pages/4_Group_Wise.py"""
from components.breakdown_page import render_breakdown
from data.loader import load_group_table
render_breakdown("Group Wise", "Pre-Medical, Pre-Engineering, General Science, Humanities, Commerce and more.", load_group_table(), "Group",
                 ["Pre-Medical", "Pre-Engineering", "General Science", "Humanities"], None, None, "grp",
                 [("medical_services", "blue"), ("engineering", "gold"), ("science", "green"), ("menu_book", "red")])
