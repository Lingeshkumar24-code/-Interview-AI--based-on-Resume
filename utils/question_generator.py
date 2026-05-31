"""
question_generator.py - AI-powered resume analysis and interview question generation
Uses Google Gemini to analyze resumes and generate personalized interview questions.
"""

import json
import re
import os
from utils.ai_client import call_ai


def _call_gemini(prompt, temperature=0.7):
    """
    Wrapper routing calls to the new Groq AI client.
    """
    return call_ai(prompt, temperature=temperature)


def _extract_json(text):
    """
    Extract JSON from Gemini response text.
    Handles markdown code blocks and raw JSON.
    """
    # Remove markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object/array in text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try JSON array
    arr_match = re.search(r'\[[\s\S]*\]', text)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass

    return None


def analyze_resume(resume_text):
    """
    Analyze resume text using Gemini and extract structured information.
    
    Args:
        resume_text (str): Raw text extracted from the PDF resume.
    
    Returns:
        dict: Structured resume data with skills, projects, certifications, etc.
    """
    prompt = f"""
You are an expert resume analyzer. Analyze the following resume text and extract all relevant information.

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "name": "candidate's full name or empty string",
  "email": "email address or empty string",
  "phone": "phone number or empty string",
  "skills": ["list", "of", "technical", "skills"],
  "programming_languages": ["Python", "Java", etc],
  "frameworks": ["Flask", "React", etc],
  "tools": ["Git", "Docker", etc],
  "databases": ["MySQL", "MongoDB", etc],
  "cloud": ["AWS", "GCP", etc],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief description",
      "technologies": ["tech1", "tech2"],
      "type": "web/mobile/ai/data/other"
    }}
  ],
  "certifications": ["cert1", "cert2"],
  "education": [
    {{
      "degree": "B.Tech/M.Tech/etc",
      "field": "Computer Science",
      "institution": "University Name",
      "year": "2024"
    }}
  ],
  "experience": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "duration": "6 months",
      "type": "internship/full-time/part-time"
    }}
  ],
  "total_experience_months": 0,
  "has_internship": true/false,
  "is_fresher": true/false
}}

Resume Text:
{resume_text}

Return ONLY the JSON. No markdown, no extra text.
"""

    response_text = _call_gemini(prompt, temperature=0.3)
    data = _extract_json(response_text)

    if not data:
        # Return minimal structure on parse failure
        return {
            "name": "", "email": "", "phone": "",
            "skills": [], "programming_languages": [], "frameworks": [],
            "tools": [], "databases": [], "cloud": [],
            "projects": [], "certifications": [], "education": [], "experience": [],
            "total_experience_months": 0, "has_internship": False, "is_fresher": True
        }

    return data


def determine_difficulty(resume_data):
    """
    Determine interview difficulty based on resume data.
    
    Logic:
    - Fresher: No experience, ≤ 2 projects, < 2 certifications
    - Intermediate: 1-2 years experience OR internship + multiple projects
    - Advanced: 2+ years, multiple certifications, senior roles
    
    Returns:
        str: 'fresher', 'intermediate', or 'advanced'
    """
    experience_months = resume_data.get('total_experience_months', 0)
    num_projects = len(resume_data.get('projects', []))
    num_certs = len(resume_data.get('certifications', []))
    has_internship = resume_data.get('has_internship', False)
    experience_entries = resume_data.get('experience', [])

    # Count full-time experience separately
    fulltime_entries = [e for e in experience_entries if e.get('type') == 'full-time']

    if len(fulltime_entries) >= 2 or experience_months >= 24:
        return 'advanced'
    elif has_internship or len(fulltime_entries) >= 1 or num_projects >= 3 or num_certs >= 2:
        return 'intermediate'
    else:
        return 'fresher'


def generate_interview_questions(resume_data, difficulty='fresher', num_questions=12):
    """
    Generate personalized interview questions based on resume data and difficulty.
    
    Returns:
        list of dicts: [{ 'text': str, 'type': str, 'order': int }]
    """
    skills = ', '.join(resume_data.get('skills', []) + resume_data.get('programming_languages', []))
    frameworks = ', '.join(resume_data.get('frameworks', []))
    tools = ', '.join(resume_data.get('tools', []))
    projects_text = json.dumps(resume_data.get('projects', []))
    certs = ', '.join(resume_data.get('certifications', []))

    difficulty_guidance = {
        'fresher': 'Focus on fundamentals, basic concepts, and definitions. Avoid advanced system design.',
        'intermediate': 'Mix of concepts, implementation details, and practical experience questions.',
        'advanced': 'Deep dive into architecture, system design, optimizations, and leadership experience.'
    }

    prompt = f"""
You are an expert technical interviewer. Generate exactly {num_questions} personalized interview questions
for a candidate based on their resume.

Candidate Profile:
- Skills: {skills}
- Frameworks: {frameworks}
- Tools: {tools}
- Projects: {projects_text}
- Certifications: {certs}
- Difficulty Level: {difficulty} — {difficulty_guidance.get(difficulty, '')}

Generate a BALANCED mix:
- 40% Technical questions (based on specific skills and technologies in resume)
- 30% Project questions (ask about each project specifically)
- 30% HR/Behavioral questions (career goals, teamwork, problem-solving, strengths)

Return ONLY a valid JSON array with this exact structure:
[
  {{
    "text": "Full question text here",
    "type": "technical"
  }},
  {{
    "text": "Tell me about the AI Chatbot project you built...",
    "type": "project"
  }},
  {{
    "text": "What is your greatest professional strength?",
    "type": "hr"
  }}
]

Rules:
- Questions MUST be specific to this exact resume (mention specific skills, project names, companies)
- No generic questions that could apply to any candidate
- Make project questions reference the actual project names from their resume
- Technical questions should reference their actual listed skills
- HR questions should be personalized based on their background
- Return ONLY the JSON array, no markdown, no explanations
"""

    response_text = _call_gemini(prompt, temperature=0.8)
    questions_data = _extract_json(response_text)

    if not questions_data or not isinstance(questions_data, list):
        # Fallback to basic questions
        questions_data = [
            {"text": "Tell me about yourself and your background.", "type": "hr"},
            {"text": "What are your strongest technical skills?", "type": "technical"},
            {"text": "Where do you see yourself in 5 years?", "type": "hr"}
        ]

    # Normalize and add order
    questions = []
    for i, q in enumerate(questions_data[:num_questions]):
        questions.append({
            'text': q.get('text', '').strip(),
            'type': q.get('type', 'technical').lower(),
            'order': i + 1
        })

    return questions


def generate_followup_question(question, answer, resume_context=""):
    """
    Generate a dynamic follow-up question based on the user's answer.
    
    Args:
        question (str): The original question asked.
        answer (str): The user's answer.
        resume_context (str): Brief resume context for personalization.
    
    Returns:
        str: A follow-up question, or None if no follow-up is warranted.
    """
    prompt = f"""
You are a technical interviewer. The candidate just answered a question.

Original Question: {question}

Candidate's Answer: {answer}

Resume Context: {resume_context}

Based on the candidate's answer, generate ONE follow-up question that:
1. Digs deeper into a concept they mentioned (e.g., if they said "Spring Boot", ask about "Dependency Injection")
2. Challenges any unclear or incomplete parts of their answer
3. Explores a related technical concept they should know given their background

If the answer is complete and no meaningful follow-up is needed, return: null

Return ONLY:
- A single follow-up question as plain text, OR
- The word: null

No explanations, no markdown.
"""

    try:
        response = _call_gemini(prompt, temperature=0.6)
        if response.strip().lower() in ['null', 'none', '']:
            return None
        # Clean up any quotes
        return response.strip().strip('"').strip("'")
    except Exception:
        return None
