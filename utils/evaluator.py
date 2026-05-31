"""
evaluator.py - AI-powered answer evaluation and final report generation
Uses Google Gemini to evaluate interview answers and generate comprehensive reports.
"""

import json
import re
import os
from utils.ai_client import call_ai


def _call_gemini(prompt, temperature=0.5):
    """
    Wrapper routing calls to the new Groq AI client.
    """
    return call_ai(prompt, temperature=temperature)


def _extract_json(text):
    """Extract JSON from Gemini response text."""
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return None


# ═══════════════════════════════════════════════
# ANSWER EVALUATION
# ═══════════════════════════════════════════════

def evaluate_answer(question, answer, question_type='technical', resume_context="", difficulty='fresher'):
    """
    Evaluate a candidate's answer using Gemini AI.

    Returns:
        dict: score, strengths, missing, improved_answer, communication_score, confidence_score
    """
    if not answer or len(answer.strip()) < 5:
        return {
            'score': 0, 'communication_score': 0, 'confidence_score': 0,
            'strengths': [], 'missing': ['No answer provided'],
            'improved_answer': 'Please provide a detailed answer to this question.',
            'brief_feedback': 'No answer was provided.'
        }

    evaluation_criteria = {
        'technical': 'Technical accuracy, depth of knowledge, correct terminology, and completeness',
        'project': 'Understanding of the project scope, technical decisions, challenges faced, and outcomes',
        'hr': 'Communication clarity, relevance to the question, professional attitude, and structure',
        'followup': 'Technical accuracy, ability to expand on previously mentioned concepts'
    }

    prompt = f"""
You are an expert {difficulty}-level technical interviewer evaluating a candidate's answer.

Question: {question}
Question Type: {question_type}
Candidate Level: {difficulty}
Resume Context: {resume_context}

Candidate's Answer:
"{answer}"

Evaluate based on: {evaluation_criteria.get(question_type, evaluation_criteria['technical'])}

Return ONLY a valid JSON object (no markdown):
{{
  "score": <integer 1-10>,
  "communication_score": <integer 1-10>,
  "confidence_score": <integer 1-10>,
  "strengths": ["Specific strength 1", "Specific strength 2"],
  "missing": ["Important missing point", "Key concept not mentioned"],
  "improved_answer": "A model answer demonstrating an ideal response. 3-5 sentences, comprehensive.",
  "key_concepts_to_know": ["Concept 1", "Concept 2", "Concept 3"],
  "brief_feedback": "One sentence of encouraging, constructive feedback"
}}

Scoring: 9-10 Excellent | 7-8 Good | 5-6 Adequate | 3-4 Poor | 1-2 Very poor | 0 No answer
For fresher level, be encouraging. For advanced, be strict.
Return ONLY the JSON.
"""

    response_text = _call_gemini(prompt, temperature=0.4)
    evaluation = _extract_json(response_text)

    if not evaluation:
        return {
            'score': 5, 'communication_score': 5, 'confidence_score': 5,
            'strengths': ['Answer was provided'], 'missing': ['Could not fully evaluate'],
            'improved_answer': answer, 'key_concepts_to_know': [], 'brief_feedback': 'Answer received.'
        }

    evaluation['score'] = max(0, min(10, int(evaluation.get('score', 5))))
    evaluation['communication_score'] = max(0, min(10, int(evaluation.get('communication_score', 5))))
    evaluation['confidence_score'] = max(0, min(10, int(evaluation.get('confidence_score', 5))))
    evaluation['strengths'] = evaluation.get('strengths', []) or []
    evaluation['missing'] = evaluation.get('missing', []) or []
    evaluation['improved_answer'] = evaluation.get('improved_answer', '') or ''
    evaluation['key_concepts_to_know'] = evaluation.get('key_concepts_to_know', []) or []
    evaluation['brief_feedback'] = evaluation.get('brief_feedback', '') or ''

    return evaluation


# ═══════════════════════════════════════════════
# FINAL REPORT GENERATION
# ═══════════════════════════════════════════════

def generate_final_report(session_data, answers_with_evaluations, resume_data):
    """
    Generate a comprehensive final interview report including:
    - Scores (overall, technical, project, communication, confidence, HR)
    - Strengths & weaknesses
    - Interview narrative summary
    - Per-question improvement guide with ideal answers
    - Group Discussion round guide
    - All interview rounds preparation guide (Technical, Coding, HR, Managerial)
    """
    if not answers_with_evaluations:
        return _empty_report()

    # ─── Step 1: Calculate Score Averages ───
    technical_answers = [a for a in answers_with_evaluations if a.get('question_type') in ('technical', 'followup')]
    project_answers   = [a for a in answers_with_evaluations if a.get('question_type') == 'project']
    hr_answers        = [a for a in answers_with_evaluations if a.get('question_type') == 'hr']

    def avg(lst, key='score'):
        vals = [a.get(key, 0) for a in lst if a.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else 0

    technical_score     = avg(technical_answers)
    project_score       = avg(project_answers)
    hr_score            = avg(hr_answers)
    communication_score = avg(answers_with_evaluations, 'communication_score')
    confidence_score    = avg(answers_with_evaluations, 'confidence_score')

    if technical_answers and project_answers and hr_answers:
        overall_score = (technical_score * 0.4 + project_score * 0.3 + hr_score * 0.2 + communication_score * 0.1)
    else:
        overall_score = avg(answers_with_evaluations)
    overall_score = round(overall_score, 1)

    difficulty = session_data.get('difficulty', 'fresher')
    name       = resume_data.get('name', 'The candidate')

    # ─── Step 2: Main Insights + Interview Summary (single Gemini call) ───
    qa_summary = [
        {
            'q': a.get('question_text', '')[:120],
            'type': a.get('question_type', 'technical'),
            'score': a.get('score', 0),
            'missing': (a.get('missing', []) or [])[:2]
        }
        for a in answers_with_evaluations[:10]
    ]
    skills = ', '.join((resume_data.get('skills', []) + resume_data.get('programming_languages', []))[:10])

    insights_prompt = f"""
You are a senior technical interviewer writing a post-interview assessment for {name}.

Profile:
- Skills: {skills}
- Difficulty Level: {difficulty}
- Technical Score: {technical_score}/10
- Project Score: {project_score}/10
- HR Score: {hr_score}/10
- Communication Score: {communication_score}/10
- Confidence Score: {confidence_score}/10
- Overall Score: {overall_score}/10

Q&A Performance (question, type, score, gaps):
{json.dumps(qa_summary, indent=2)}

Return ONLY a valid JSON object:
{{
  "strengths": ["Specific strength observed (3-4 items)"],
  "weaknesses": ["Specific weakness observed (2-3 items)"],
  "recommendations": [
    {{
      "topic": "Topic Name",
      "reason": "Why based on performance gaps",
      "resources": ["Resource 1", "Resource 2"]
    }}
  ],
  "overall_assessment": "2-3 sentence assessment of the candidate",
  "hiring_recommendation": "Strong Hire / Hire / Maybe / No Hire",
  "interview_summary": "Write a detailed 3-paragraph narrative: para1=overall impression and what went well, para2=technical depth demonstrated, para3=areas for growth and what to focus on next. Be specific to their profile and answers. Reference actual scores.",
  "interview_improvement_tips": [
    "Specific actionable tip 1 for their next interview",
    "Specific actionable tip 2",
    "Specific actionable tip 3",
    "Specific actionable tip 4"
  ]
}}

Return ONLY the JSON.
"""

    try:
        insights_text = _call_gemini(insights_prompt, temperature=0.5)
        report_insights = _extract_json(insights_text)
    except Exception:
        report_insights = None

    if not report_insights:
        report_insights = {
            'strengths': ['Completed the interview session'],
            'weaknesses': ['Needs more practice'],
            'recommendations': [{'topic': 'Interview Practice', 'reason': 'Regular practice improves performance', 'resources': ['LeetCode', 'GeeksForGeeks']}],
            'overall_assessment': 'Candidate completed the interview session.',
            'hiring_recommendation': 'Maybe',
            'interview_summary': 'The interview has been completed. Review your scores and the detailed feedback for each question below.',
            'interview_improvement_tips': ['Practice answering out loud', 'Use the STAR method for behavioral questions']
        }

    # ─── Step 3: Per-Question Improvement Guide (from existing evaluated data) ───
    per_question_improvements = _build_per_question_guide(answers_with_evaluations)

    # ─── Step 4: GD Round + All Interview Rounds Guide (one Gemini call) ───
    gd_rounds_data = _generate_gd_and_rounds_guide(resume_data, overall_score, difficulty)

    return {
        # Core scores
        'overall_score':       overall_score,
        'technical_score':     technical_score,
        'project_score':       project_score,
        'communication_score': communication_score,
        'confidence_score':    confidence_score,
        'hr_score':            hr_score,
        # Insights
        'strengths':                 report_insights.get('strengths', []),
        'weaknesses':                report_insights.get('weaknesses', []),
        'recommendations':           report_insights.get('recommendations', []),
        'overall_assessment':        report_insights.get('overall_assessment', ''),
        'hiring_recommendation':     report_insights.get('hiring_recommendation', 'Maybe'),
        # New comprehensive fields
        'interview_summary':         report_insights.get('interview_summary', ''),
        'interview_improvement_tips': report_insights.get('interview_improvement_tips', []),
        'per_question_improvements': per_question_improvements,
        'gd_round':                  gd_rounds_data.get('gd_round', {}),
        'rounds_guide':              gd_rounds_data.get('rounds', []),
    }


def _build_per_question_guide(answers_with_evaluations):
    """
    Build per-question improvement guide from already-evaluated answer data.
    No additional Gemini calls needed — uses existing evaluation fields.
    """
    guide = []
    for a in answers_with_evaluations:
        guide.append({
            'question_id':    a.get('question_id', 0),
            'question':       a.get('question_text', ''),
            'question_type':  a.get('question_type', 'technical'),
            'your_answer':    a.get('answer_text', ''),
            'score':          a.get('score', 0),
            'what_was_good':  a.get('strengths', []) or [],
            'what_to_improve': a.get('missing', []) or [],
            'ideal_answer':   a.get('improved_answer', '') or '',
            'key_concepts':   a.get('key_concepts_to_know', []) or [],
        })
    return guide


def _generate_gd_and_rounds_guide(resume_data, overall_score, difficulty):
    """
    Generate Group Discussion topics and all interview rounds preparation guide.
    Entirely based on the candidate's resume skills and domain.
    """
    skills     = ', '.join((resume_data.get('skills', []) + resume_data.get('programming_languages', []))[:10])
    frameworks = ', '.join(resume_data.get('frameworks', [])[:5])
    tools      = ', '.join(resume_data.get('tools', [])[:5])
    projects   = resume_data.get('projects', [])
    proj_names = ', '.join([p.get('name', '') for p in projects[:3]])
    education  = resume_data.get('education', [{}])
    field      = education[0].get('field', 'Computer Science') if education else 'Computer Science'
    certs      = ', '.join(resume_data.get('certifications', [])[:3])

    prompt = f"""
You are a career coach and interview expert. Generate a complete interview preparation guide for this candidate.

Candidate Profile:
- Field of Study: {field}
- Technical Skills: {skills}
- Frameworks: {frameworks}
- Tools: {tools}
- Projects: {proj_names}
- Certifications: {certs}
- Interview Level: {difficulty}
- Score Achieved: {overall_score}/10

Generate ALL content SPECIFIC to their actual skills, projects, and domain.

Return ONLY valid JSON in this exact structure:
{{
  "gd_round": {{
    "what_is_gd": "1-2 sentence explanation of what GD round tests",
    "how_to_win": "2-3 sentence strategy for excelling in GD",
    "tips": [
      "Specific GD tip 1",
      "Specific GD tip 2",
      "Specific GD tip 3",
      "Specific GD tip 4",
      "Specific GD tip 5"
    ],
    "topics": [
      {{
        "topic": "Topic title (must be relevant to their field/skills)",
        "category": "Technology / Business / Social / Current Affairs",
        "why_relevant": "Why this suits someone with their background",
        "key_points": [
          "Strong point to make with data/example",
          "Counter-perspective to consider",
          "Conclusion or solution point"
        ],
        "opening_line": "A strong, confident opening statement for this topic",
        "do_mention": ["Specific thing to mention 1", "Specific thing 2"],
        "avoid_saying": "Common mistake candidates make on this topic"
      }}
    ]
  }},
  "rounds": [
    {{
      "round_name": "Technical Round 1",
      "round_icon": "Technical",
      "description": "What happens in this round specifically for their profile",
      "duration": "45-60 minutes",
      "focus_areas": [
        "Specific topic from their actual skills",
        "Another specific area",
        "Third focus area"
      ],
      "sample_questions": [
        "Question directly about their listed skill/project?",
        "Another specific question?",
        "Third question?"
      ],
      "preparation_tips": [
        "Specific prep tip 1",
        "Specific prep tip 2",
        "Specific prep tip 3"
      ],
      "days_to_prepare": "7-10 days",
      "priority": "High"
    }},
    {{
      "round_name": "Coding / DSA Round",
      "round_icon": "Coding",
      "description": "What to expect in coding assessment",
      "duration": "60-90 minutes",
      "focus_areas": [
        "DSA topic relevant to their language",
        "Problem-solving approach",
        "Time/space complexity"
      ],
      "sample_questions": [
        "Problem type 1 in their language",
        "Problem type 2",
        "Problem type 3"
      ],
      "preparation_tips": [
        "Prep tip 1",
        "Prep tip 2",
        "Prep tip 3"
      ],
      "days_to_prepare": "14-21 days",
      "priority": "High"
    }},
    {{
      "round_name": "HR Round",
      "round_icon": "HR",
      "description": "Behavioral and culture-fit assessment",
      "duration": "30-45 minutes",
      "focus_areas": [
        "Communication skills",
        "Career motivation",
        "Team collaboration"
      ],
      "sample_questions": [
        "Tell me about yourself",
        "Why do you want to join us?",
        "Where do you see yourself in 5 years?",
        "Describe a challenge you overcame"
      ],
      "preparation_tips": [
        "Prepare your 2-minute self-introduction",
        "Research the company before the interview",
        "Use STAR method for behavioral questions"
      ],
      "days_to_prepare": "2-3 days",
      "priority": "Medium"
    }},
    {{
      "round_name": "Managerial Round",
      "round_icon": "Managerial",
      "description": "Problem-solving and situational assessment",
      "duration": "30-45 minutes",
      "focus_areas": [
        "Situational judgment",
        "Team dynamics",
        "Decision making"
      ],
      "sample_questions": [
        "How would you handle a disagreement with a teammate?",
        "Describe a situation where you led a project",
        "How do you prioritize tasks under pressure?"
      ],
      "preparation_tips": [
        "Prepare specific examples from your projects",
        "Think about leadership moments in college/work",
        "Practice situational responses"
      ],
      "days_to_prepare": "3-5 days",
      "priority": "Medium"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- Generate EXACTLY 4 GD topics, all specific to their field ({field}) and skills ({skills})
- All sample questions MUST reference their actual listed technologies
- All prep tips must be actionable and specific
- Do NOT use generic placeholders
Return ONLY the JSON.
"""

    try:
        response_text = _call_gemini(prompt, temperature=0.7)
        data = _extract_json(response_text)
        if data:
            return data
    except Exception as e:
        print(f"GD/Rounds guide error (non-critical): {e}")

    # Fallback
    return {
        'gd_round': {
            'what_is_gd': 'A Group Discussion round tests your communication, analytical thinking, and leadership ability.',
            'how_to_win': 'Speak clearly, listen actively, and back your points with specific examples.',
            'tips': ['Start with a strong opening', 'Listen before responding', 'Use data to back your points', 'Summarize the discussion at the end'],
            'topics': [
                {
                    'topic': 'AI and the Future of Software Development',
                    'category': 'Technology',
                    'why_relevant': 'Directly relevant to your technical background',
                    'key_points': ['AI is automating repetitive coding tasks', 'Developers need to upskill in AI/ML', 'Ethics and bias in AI systems'],
                    'opening_line': 'AI is not replacing developers — it is amplifying what great developers can do.',
                    'do_mention': ['GitHub Copilot', 'Prompt engineering'],
                    'avoid_saying': 'AI will completely replace programmers'
                }
            ]
        },
        'rounds': []
    }


def _empty_report():
    """Return an empty report structure."""
    return {
        'overall_score': 0, 'technical_score': 0, 'project_score': 0,
        'communication_score': 0, 'confidence_score': 0, 'hr_score': 0,
        'strengths': [], 'weaknesses': [], 'recommendations': [],
        'overall_assessment': 'No answers recorded.',
        'hiring_recommendation': 'No Hire',
        'interview_summary': '',
        'interview_improvement_tips': [],
        'per_question_improvements': [],
        'gd_round': {},
        'rounds_guide': [],
    }
