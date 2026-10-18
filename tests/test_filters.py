"""Title filter for the tech-wide scope: what must be kept and what must be dropped."""
import pytest

from jobradar.filters import is_tech_role

KEEP = [
    # data (unchanged scope)
    "Senior Data Engineer", "Analytics Engineer (dbt)", "BI Developer", "Data Scientist",
    "Machine Learning Engineer", "Dateningenieur (m/w/d)", "Data Warehouse Lead",
    # software engineering
    "Senior Backend Engineer (Go)", "Frontend Developer - React", "Full Stack Engineer",
    "Software Engineer II", "iOS Developer", "Android Engineer", "Flutter Developer",
    "Senior Java Developer", ".NET Developer", "Staff Software Engineer, Payments",
    "Embedded Software Engineer (Automotive)", "Engineering Manager, Platform",
    "Softwareentwickler (m/w/d)", "Développeur Full Stack", "Desarrollador Backend",
    "Web Developer", "PHP Developer (Laravel)", "Python Developer", "C# Developer", "C++ Engineer",
    # QA / testing
    "QA Automation Engineer", "Manual QA Tester", "Software Test Engineer", "SDET",
    "Quality Assurance Analyst", "Test Automation Engineer (Playwright)", "Testautomatisierer (m/w/d)",
    # UI / UX design
    "Senior Product Designer", "UX/UI Designer", "UI Designer", "UX Researcher",
    "Interaction Designer", "Design Systems Lead",
    # devops / cloud / security / IT
    "DevOps Engineer", "Site Reliability Engineer", "Cloud Architect (AWS)", "Platform Engineer",
    "Security Engineer", "SOC Analyst", "Penetration Tester", "Cybersecurity Specialist",
    "System Administrator", "IT Support Specialist", "Network Engineer",
    # AI roles with an engineering / data word stay; agile delivery is collected too
    "AI Engineer", "AI Safety Engineer (Data)", "AI/Agent Engineers", "Head of AI Research",
    "Machine Learning Engineer, Growth", "Scrum Master", "Agile Coach",
    # ERP & CRM, networks & telecom, product & delivery, databases, docs, web3
    "SAP FICO Consultant", "Salesforce Developer", "Dynamics 365 Functional Consultant", "ABAP Developer",
    "ServiceNow Developer", "Odoo Developer", "NOC Engineer", "RF Optimization Engineer", "Telecom Engineer",
    "Database Administrator", "Product Owner", "Technical Project Manager", "Technical Writer",
    "Blockchain Developer", "MLOps Engineer",
]

DROP = [
    "Mechanical Engineer", "Civil Engineer", "Electrical Engineer", "Process Engineer",
    "Manufacturing Engineer", "Fashion Designer", "Interior Designer", "Graphic Designer",
    "Sales Manager", "Account Executive", "Warehouse Associate II", "Truck Driver",
    "Registered Nurse", "Chef de Partie", "Recruiter", "HR Business Partner", "Data Entry Clerk",
    "Field Service Technician", "Test Driver", "Clinical Research Associate", "", None,
    # business jobs that only mention AI, physical warehouse jobs, admin "data" jobs
    "AI Strategist", "AI Trainers Network - English", "AI Transformation Leader", "AI GTM Specialist",
    "Growth Marketer- Reception.ai", "Senior AI Specialist (Operations)", "AI Talent Pool",
    "Analytical Chemistry Specialist - Freelance AI Trainer Project", "Warehouse Employee",
    "Data Assistant", "Medical Data Officer",
    "Construction Project Manager", "Marketing Project Manager", "Product Marketing Manager",
]


@pytest.mark.parametrize("title", KEEP)
def test_tech_titles_are_kept(title):
    assert is_tech_role(title), title


@pytest.mark.parametrize("title", DROP)
def test_non_tech_titles_are_dropped(title):
    assert not is_tech_role(title), title


@pytest.mark.parametrize("title", [
    "ASIC Design Engineer", "FPGA Engineer", "Design Verification Engineer (UVM)", "Physical Design Engineer",
    "AUTOSAR Software Engineer", "ADAS Engineer", "SOC Analyst L2", "Security Analyst", "Red Team Operator",
    "GRC Specialist", "IT Auditor", "IAM Engineer", "Pre-Sales Engineer", "Solutions Consultant",
    "Enterprise Architect", "Integration Developer (MuleSoft)", "Developer Advocate", "Quantitative Developer",
    "Performance Test Engineer", "UX Writer", "IT Manager", "Head of IT", "Computer Vision Engineer",
    "NLP Engineer", "LLM Engineer", "Speech Recognition Engineer", "Customer Support Engineer",
])
def test_specialist_tech_titles_are_kept(title):
    assert is_tech_role(title)


@pytest.mark.parametrize("title", ["Sales Manager", "Electrical Engineer", "Civil Engineer", "Security Guard",
                                   "Landscape Architect"])
def test_lookalike_non_tech_titles_stay_out(title):
    assert not is_tech_role(title)


def test_guard_style_security_jobs_are_not_tech():
    assert not is_tech_role("Security Officer")
    assert not is_tech_role("Security Supervisor - Mall")
    assert is_tech_role("Information Security Officer") and is_tech_role("Cyber Security Specialist")
