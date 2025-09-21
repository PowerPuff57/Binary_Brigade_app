import streamlit as st
import re
import json
import hashlib
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import tempfile
import os

# Document Processing
try:
    import PyPDF2
    import pdfplumber
    import docx2txt
    from docx import Document
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Configure Streamlit
st.set_page_config(
    page_title="Resume Relevance Check System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-high {
        color: #10b981;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .score-medium {
        color: #f59e0b;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .score-low {
        color: #ef4444;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .skill-tag {
        background: #e0e7ff;
        color: #4338ca;
        padding: 0.25rem 0.5rem;
        border-radius: 10px;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.8rem;
    }
    .missing-skill {
        background: #fee2e2;
        color: #dc2626;
    }
</style>
""", unsafe_allow_html=True)

# Data Classes
@dataclass
class JobDescription:
    id: str
    title: str
    company: str
    must_have_skills: List[str]
    good_to_have_skills: List[str]
    experience_required: str
    description: str
    location: str

@dataclass
class Resume:
    id: str
    name: str
    email: str
    skills: List[str]
    experience: List[Dict]
    education: List[Dict]
    projects: List[Dict]
    raw_text: str

@dataclass
class EvaluationResult:
    resume_id: str
    job_id: str
    relevance_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    verdict: str
    feedback: str
    suggestions: List[str]

# Document Processing
class DocumentProcessor:
    @staticmethod
    def extract_text_from_pdf(file_bytes) -> str:
        if not PDF_AVAILABLE:
            return ""
        
        text = ""
        try:
            # Try pdfplumber first
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name
            
            try:
                with pdfplumber.open(tmp_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except:
                # Fallback to PyPDF2
                with open(tmp_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
            
            os.unlink(tmp_path)
        except Exception as e:
            st.error(f"PDF processing failed: {str(e)}")
        
        return text.strip()
    
    @staticmethod
    def extract_text_from_docx(file_bytes) -> str:
        text = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name
            
            try:
                text = docx2txt.process(tmp_path)
                if not text:
                    doc = Document(tmp_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                st.error(f"DOCX processing failed: {str(e)}")
            
            os.unlink(tmp_path)
        except Exception as e:
            st.error(f"File processing failed: {str(e)}")
        
        return text.strip()
    
    @staticmethod
    def extract_text(uploaded_file) -> str:
        if uploaded_file is None:
            return ""
        
        file_ext = uploaded_file.name.split('.')[-1].lower()
        file_bytes = uploaded_file.getvalue()
        
        if file_ext == 'pdf':
            return DocumentProcessor.extract_text_from_pdf(file_bytes)
        elif file_ext in ['docx', 'doc']:
            return DocumentProcessor.extract_text_from_docx(file_bytes)
        elif file_ext == 'txt':
            return file_bytes.decode('utf-8')
        else:
            st.error(f"Unsupported file format: {file_ext}")
            return ""

# Parsing Classes
class ResumeParser:
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]')
    
    def parse(self, text: str) -> Resume:
        text = self._clean_text(text)
        
        resume_id = hashlib.md5(f"{text[:100]}_{datetime.now()}".encode()).hexdigest()[:12]
        
        return Resume(
            id=resume_id,
            name=self._extract_name(text),
            email=self._extract_email(text),
            skills=self._extract_skills(text),
            experience=self._extract_experience(text),
            education=self._extract_education(text),
            projects=self._extract_projects(text),
            raw_text=text
        )
    
    def _clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()
    
    def _extract_name(self, text: str) -> str:
        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line.split()) <= 4 and len(first_line) > 2:
                return first_line
        return "Unknown Candidate"
    
    def _extract_email(self, text: str) -> str:
        matches = self.email_pattern.findall(text)
        return matches[0] if matches else "No email found"
    
    def _extract_skills(self, text: str) -> List[str]:
        # Common technical skills
        tech_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'django', 'flask', 'spring', 'docker', 'kubernetes', 'aws', 'azure',
            'gcp', 'git', 'jenkins', 'machine learning', 'deep learning', 'nlp',
            'data science', 'sql', 'mongodb', 'postgresql', 'mysql', 'html', 'css',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'c++',
            'devops', 'agile', 'scrum', 'analytics', 'tableau', 'powerbi'
        ]
        
        skills = []
        text_lower = text.lower()
        
        # Find skills mentioned in text
        for skill in tech_skills:
            if skill in text_lower:
                skills.append(skill)
        
        # Look for skills section
        skills_match = re.search(r'skills?\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)', text, re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(1)
            extracted_skills = re.split(r'[,;\|\n•\-]', skills_text)
            for skill in extracted_skills:
                clean_skill = skill.strip().lower()
                if len(clean_skill) > 2 and clean_skill not in skills:
                    skills.append(clean_skill)
        
        return list(set(skills))
    
    def _extract_experience(self, text: str) -> List[Dict]:
        experience = []
        exp_match = re.search(r'experience\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)', text, re.IGNORECASE)
        if exp_match:
            exp_text = exp_match.group(1)
            experience.append({"description": exp_text[:300]})
        return experience
    
    def _extract_education(self, text: str) -> List[Dict]:
        education = []
        degrees = ['bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'mba', 'b.e', 'm.e', 'bsc', 'msc']
        text_lower = text.lower()
        
        for degree in degrees:
            if degree in text_lower:
                education.append({"degree": degree.upper()})
        
        return education
    
    def _extract_projects(self, text: str) -> List[Dict]:
        projects = []
        project_match = re.search(r'projects?\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)', text, re.IGNORECASE)
        if project_match:
            project_text = project_match.group(1)
            projects.append({"description": project_text[:300]})
        return projects

class JobDescriptionParser:
    def parse(self, text: str, company: str = "", location: str = "") -> JobDescription:
        text = self._clean_text(text)
        jd_id = hashlib.md5(f"{company}_{text[:100]}_{datetime.now()}".encode()).hexdigest()[:12]
        
        return JobDescription(
            id=jd_id,
            title=self._extract_title(text),
            company=company,
            must_have_skills=self._extract_must_have_skills(text),
            good_to_have_skills=self._extract_good_to_have_skills(text),
            experience_required=self._extract_experience_requirement(text),
            description=text,
            location=location
        )
    
    def _clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()
    
    def _extract_title(self, text: str) -> str:
        title_patterns = [
            r'job\s*title\s*:?\s*([^\n]+)',
            r'position\s*:?\s*([^\n]+)',
            r'role\s*:?\s*([^\n]+)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback to first line
        lines = text.split('\n')
        if lines and len(lines[0]) <= 80:
            return lines[0].strip()
        
        return "Software Developer"
    
    def _extract_must_have_skills(self, text: str) -> List[str]:
        patterns = [
            r'required\s*skills?\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
            r'must\s*have\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
            r'mandatory\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
        ]
        
        skills = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                skills_text = match.group(1)
                extracted = re.split(r'[,;\|\n•\-]', skills_text)
                skills.extend([s.strip().lower() for s in extracted if s.strip() and len(s.strip()) > 2])
                break
        
        # If no specific section found, extract common tech skills
        if not skills:
            tech_skills = ['python', 'java', 'javascript', 'react', 'sql', 'aws', 'docker']
            text_lower = text.lower()
            skills = [skill for skill in tech_skills if skill in text_lower]
        
        return list(set(skills))[:15]
    
    def _extract_good_to_have_skills(self, text: str) -> List[str]:
        patterns = [
            r'good\s*to\s*have\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
            r'preferred\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
            r'nice\s*to\s*have\s*:?\s*([^\n]+(?:\n[^\n]*)*?)(?:\n\s*\n|\Z)',
        ]
        
        skills = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                skills_text = match.group(1)
                extracted = re.split(r'[,;\|\n•\-]', skills_text)
                skills.extend([s.strip().lower() for s in extracted if s.strip() and len(s.strip()) > 2])
                break
        
        return list(set(skills))[:10]
    
    def _extract_experience_requirement(self, text: str) -> str:
        exp_patterns = [
            r'(\d+[\+\-]?\d*)\s*years?\s*(?:of\s*)?experience',
            r'experience\s*:?\s*(\d+[\+\-]?\d*)\s*years?',
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) + " years"
        
        return "Not specified"

# Evaluation Class
class RelevanceEvaluator:
    def evaluate(self, resume: Resume, job_desc: JobDescription) -> EvaluationResult:
        # Calculate skill matches
        resume_skills = set([s.lower() for s in resume.skills])
        must_have_skills = set([s.lower() for s in job_desc.must_have_skills])
        good_to_have_skills = set([s.lower() for s in job_desc.good_to_have_skills])
        
        matched_must_have = resume_skills.intersection(must_have_skills)
        matched_good_to_have = resume_skills.intersection(good_to_have_skills)
        matched_skills = list(matched_must_have.union(matched_good_to_have))
        
        missing_must_have = must_have_skills - resume_skills
        missing_skills = list(missing_must_have)
        
        # Calculate score
        score = 0
        
        # Must-have skills (50 points)
        if must_have_skills:
            score += (len(matched_must_have) / len(must_have_skills)) * 50
        
        # Good-to-have skills (20 points)
        if good_to_have_skills:
            score += (len(matched_good_to_have) / len(good_to_have_skills)) * 20
        
        # Experience (15 points)
        if resume.experience:
            score += 15
        
        # Education (10 points)
        if resume.education:
            score += 10
        
        # Projects (5 points)
        if resume.projects:
            score += 5
        
        score = min(100, score)
        verdict = "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW"
        
        feedback = self._generate_feedback(score, matched_skills, missing_skills)
        suggestions = self._generate_suggestions(missing_skills, resume)
        
        return EvaluationResult(
            resume_id=resume.id,
            job_id=job_desc.id,
            relevance_score=round(score, 2),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            verdict=verdict,
            feedback=feedback,
            suggestions=suggestions
        )
    
    def _generate_feedback(self, score: float, matched_skills: List[str], missing_skills: List[str]) -> str:
        feedback = f"Overall relevance score: {score:.1f}%"
        if matched_skills:
            feedback += f" | Matched {len(matched_skills)} skills"
        if missing_skills:
            feedback += f" | Missing {len(missing_skills)} key skills"
        return feedback
    
    def _generate_suggestions(self, missing_skills: List[str], resume: Resume) -> List[str]:
        suggestions = []
        
        if missing_skills:
            suggestions.append(f"Learn these key skills: {', '.join(missing_skills[:3])}")
        
        if not resume.projects:
            suggestions.append("Add relevant projects to showcase your skills")
        
        if not resume.experience:
            suggestions.append("Gain practical experience through internships or freelance work")
        
        suggestions.append("Optimize your resume keywords for better ATS compatibility")
        
        return suggestions

# Initialize session state
if 'job_descriptions' not in st.session_state:
    st.session_state.job_descriptions = []
if 'evaluations' not in st.session_state:
    st.session_state.evaluations = []

# Initialize parsers
resume_parser = ResumeParser()
job_parser = JobDescriptionParser()
evaluator = RelevanceEvaluator()

# Main App
def main():
    st.markdown('<h1 class="main-header">🎯 Resume Relevance Check System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Resume Evaluation for HR Teams</p>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page:", [
        "Upload Job Description", 
        "Upload Resume", 
        "View Results",
        "About"
    ])
    
    if page == "Upload Job Description":
        upload_job_description()
    elif page == "Upload Resume":
        upload_resume()
    elif page == "View Results":
        view_results()
    else:
        about_page()

def upload_job_description():
    st.header("📋 Upload Job Description")
    
    col1, col2 = st.columns(2)
    
    with col1:
        company = st.text_input("Company Name *", placeholder="e.g., Tech Corp")
        location = st.text_input("Location", placeholder="e.g., San Francisco, CA")
    
    with col2:
        st.info("💡 Tip: Make sure to include required skills and experience clearly in your job description")
    
    # Text input or file upload
    input_method = st.radio("Choose input method:", ["Paste text", "Upload file"])
    
    jd_text = ""
    if input_method == "Paste text":
        jd_text = st.text_area(
            "Job Description Text",
            height=300,
            placeholder="Paste the complete job description here..."
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload Job Description File",
            type=['pdf', 'docx', 'txt'],
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        if uploaded_file:
            with st.spinner("Extracting text from file..."):
                jd_text = DocumentProcessor.extract_text(uploaded_file)
                if jd_text:
                    st.success("Text extracted successfully!")
                    with st.expander("Preview extracted text"):
                        st.text(jd_text[:500] + "..." if len(jd_text) > 500 else jd_text)
    
    if st.button("Parse Job Description", type="primary"):
        if not company:
            st.error("Company name is required!")
            return
        
        if not jd_text:
            st.error("Please provide job description text or upload a file!")
            return
        
        with st.spinner("Parsing job description..."):
            try:
                job_desc = job_parser.parse(jd_text, company, location)
                st.session_state.job_descriptions.append(job_desc)
                
                st.success("Job description parsed successfully!")
                
                # Display parsed information
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Job Details")
                    st.write(f"**Title:** {job_desc.title}")
                    st.write(f"**Company:** {job_desc.company}")
                    st.write(f"**Location:** {job_desc.location}")
                    st.write(f"**Experience Required:** {job_desc.experience_required}")
                
                with col2:
                    st.subheader("Required Skills")
                    if job_desc.must_have_skills:
                        skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in job_desc.must_have_skills])
                        st.markdown(skills_html, unsafe_allow_html=True)
                    else:
                        st.write("No specific skills extracted")
                    
                    if job_desc.good_to_have_skills:
                        st.subheader("Preferred Skills")
                        skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in job_desc.good_to_have_skills])
                        st.markdown(skills_html, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error parsing job description: {str(e)}")

def upload_resume():
    st.header("📄 Upload Resume for Evaluation")
    
    if not st.session_state.job_descriptions:
        st.warning("Please upload at least one job description first!")
        if st.button("Go to Job Description Upload"):
            st.rerun()
        return
    
    # Job selection
    job_options = [f"{jd.title} at {jd.company}" for jd in st.session_state.job_descriptions]
    selected_job_idx = st.selectbox("Select Job Position", range(len(job_options)), format_func=lambda x: job_options[x])
    
    selected_job = st.session_state.job_descriptions[selected_job_idx]
    
    # Display job requirements
    with st.expander("View Job Requirements"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Required Skills:**")
            if selected_job.must_have_skills:
                for skill in selected_job.must_have_skills:
                    st.write(f"• {skill}")
            else:
                st.write("None specified")
        
        with col2:
            st.write("**Preferred Skills:**")
            if selected_job.good_to_have_skills:
                for skill in selected_job.good_to_have_skills:
                    st.write(f"• {skill}")
            else:
                st.write("None specified")
    
    # Resume upload
    uploaded_resume = st.file_uploader(
        "Upload Resume",
        type=['pdf', 'docx', 'txt'],
        help="Supported formats: PDF, DOCX, TXT"
    )
    
    if uploaded_resume and st.button("Evaluate Resume", type="primary"):
        with st.spinner("Processing resume..."):
            try:
                # Extract text
                resume_text = DocumentProcessor.extract_text(uploaded_resume)
                if not resume_text:
                    st.error("Could not extract text from the resume. Please try a different file.")
                    return
                
                # Parse resume
                resume = resume_parser.parse(resume_text)
                
                # Evaluate resume
                evaluation = evaluator.evaluate(resume, selected_job)
                st.session_state.evaluations.append(evaluation)
                
                # Display results
                st.success("Resume evaluated successfully!")
                display_evaluation_result(evaluation, resume, selected_job)
                
            except Exception as e:
                st.error(f"Error processing resume: {str(e)}")

def display_evaluation_result(evaluation: EvaluationResult, resume: Resume, job: JobDescription):
    st.header("📊 Evaluation Results")
    
    # Score display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        score_class = f"score-{evaluation.verdict.lower()}"
        st.markdown(f'<p class="{score_class}">Score: {evaluation.relevance_score}%</p>', unsafe_allow_html=True)
    
    with col2:
        st.metric("Verdict", evaluation.verdict)
    
    with col3:
        st.metric("Matched Skills", len(evaluation.matched_skills))
    
    # Detailed breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Matched Skills")
        if evaluation.matched_skills:
            skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in evaluation.matched_skills])
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("No matching skills found")
    
    with col2:
        st.subheader("❌ Missing Skills")
        if evaluation.missing_skills:
            skills_html = "".join([f'<span class="skill-tag missing-skill">{skill}</span>' for skill in evaluation.missing_skills])
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("No missing skills")
    
    # Feedback and suggestions
    st.subheader("📝 Feedback")
    st.write(evaluation.feedback)
    
    st.subheader("💡 Suggestions for Improvement")
    for i, suggestion in enumerate(evaluation.suggestions, 1):
        st.write(f"{i}. {suggestion}")
    
    # Resume details
    with st.expander("View Resume Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {resume.name}")
            st.write(f"**Email:** {resume.email}")
            st.write(f"**Skills Found:** {len(resume.skills)}")
        with col2:
            st.write(f"**Experience:** {len(resume.experience)} entries")
            st.write(f"**Education:** {len(resume.education)} entries")
            st.write(f"**Projects:** {len(resume.projects)} entries")

def view_results():
    st.header("📊 All Evaluation Results")
    
    if not st.session_state.evaluations:
        st.info("No evaluations yet. Upload some resumes to see results here.")
        return
    
    # Statistics
    total = len(st.session_state.evaluations)
    high_count = len([e for e in st.session_state.evaluations if e.verdict == "HIGH"])
    medium_count = len([e for e in st.session_state.evaluations if e.verdict == "MEDIUM"])
    low_count = len([e for e in st.session_state.evaluations if e.verdict == "LOW"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Evaluations", total)
    col2.metric("High Matches", high_count)
    col3.metric("Medium Matches", medium_count)
    col4.metric("Low Matches", low_count)
    
    # Results table
    st.subheader("Evaluation Summary")
    
    results_data = []
    for eval in st.session_state.evaluations:
        # Find corresponding job
        job = next((jd for jd in st.session_state.job_descriptions if jd.id == eval.job_id), None)
        job_title = job.title if job else "Unknown Job"
        
        results_data.append({
            "Job": job_title,
            "Score": f"{eval.relevance_score}%",
            "Verdict": eval.verdict,
            "Matched Skills": len(eval.matched_skills),
            "Missing Skills": len(eval.missing_skills)
        })
    
    if results_data:
        st.dataframe(results_data, use_container_width=True)

def about_page():
    st.header("ℹ️ About Resume Relevance Check System")
    
    st.markdown("""
    ## 🎯 What is this system?
    
    The Resume Relevance Check System is an AI-powered tool that helps HR teams and recruiters 
    automatically evaluate resumes against job descriptions. It provides objective scoring and 
    actionable feedback to streamline the recruitment process.
    
    ## ✨ Key Features
    
    - **Multi-format Support**: Upload PDF, DOCX, or TXT files
    - **Intelligent Parsing**: Automatically extracts skills, experience, and qualifications
    - **Relevance Scoring**: Provides percentage match scores with detailed breakdown
    - **Skill Analysis**: Shows matched and missing skills
    - **Actionable Feedback**: Gives specific suggestions for improvement
    
    ## 🔧 How it works
    
    1. **Upload Job Description**: Parse job requirements and extract key skills
    2. **Upload Resume**: Extract candidate information and qualifications
    3. **Automated Evaluation**: Compare resume against job requirements
    4. **Get Results**: Receive detailed scoring and improvement suggestions
    
    ## 📊 Scoring System
    
    - **HIGH (75-100%)**: Strong match, recommended for interview
    - **MEDIUM (50-74%)**: Partial match, consider for further screening
    - **LOW (0-49%)**: Poor match, likely not suitable
    
    ## 🚀 Getting Started
    
    1. Start by uploading a job description
    2. Then upload resumes for evaluation
    3. View detailed results and statistics
    
    ---
    
    **Built with Streamlit** | **Version 1.0.0**
    """)

if __name__ == "__main__":
    main()
