"""
app.py - Main Flask application for InterviewAI
Interview Preparation Platform powered by Google Gemini AI
"""

import os
import json
import shutil
import tempfile
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, send_file
)
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if os.getenv('VERCEL'):
    runtime_root = os.path.join(tempfile.gettempdir(), 'interview-ai')
else:
    runtime_root = os.path.dirname(__file__)

os.makedirs(runtime_root, exist_ok=True)
os.environ.setdefault('DATABASE_PATH', os.path.join(runtime_root, 'database.db'))

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'interview-ai-secret-key-2024')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(runtime_root, 'uploads'))

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import utilities
from utils.database import (
    init_db, create_session, get_session, get_all_sessions,
    get_dashboard_stats, save_questions, get_session_questions,
    get_question, save_answer, get_session_answers, save_followup_question,
    save_report, get_report, update_session_status, update_session_completed_questions
)
from utils.pdf_parser import extract_text_from_pdf, save_uploaded_file
from utils.question_generator import analyze_resume, determine_difficulty, generate_interview_questions, generate_followup_question
from utils.evaluator import evaluate_answer, generate_final_report

# Initialize database on startup
with app.app_context():
    init_db()


# ═══════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error="Page not found"), 404


@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413


import traceback

@app.errorhandler(500)
def internal_error(e):
    traceback.print_exc()
    print(f"500 Error: {e}")
    return jsonify({'error': f'Internal server error: {str(e)}'}), 500


# ═══════════════════════════════════════════════
# MAIN ROUTES
# ═══════════════════════════════════════════════

@app.route('/')
def index():
    """Landing page with resume upload."""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard showing stats and recent interviews."""
    stats = get_dashboard_stats()
    recent_sessions = get_all_sessions()[:5]
    return render_template('dashboard.html', stats=stats, sessions=recent_sessions)


@app.route('/history')
def history():
    """Full interview history page."""
    all_sessions = get_all_sessions()
    return render_template('history.html', sessions=all_sessions)


# ═══════════════════════════════════════════════
# RESUME UPLOAD & ANALYSIS
# ═══════════════════════════════════════════════

@app.route('/upload', methods=['POST'])
def upload_resume():
    """
    Handle resume PDF upload, extract text, and analyze with Gemini.
    Returns session_id to start the interview.
    """
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded. Please select a PDF resume.'}), 400

    file = request.files['resume']

    try:
        # Save and validate the uploaded file
        filename, filepath = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        # Extract text from PDF
        resume_text = extract_text_from_pdf(filepath)

        if len(resume_text.strip()) < 100:
            os.remove(filepath)
            return jsonify({'error': 'Resume appears to be empty or unreadable. Please upload a text-based PDF.'}), 400

        # Analyze resume with Gemini AI
        resume_data = analyze_resume(resume_text)

        # Determine interview difficulty
        difficulty = determine_difficulty(resume_data)

        # Generate personalized questions
        questions_list = generate_interview_questions(resume_data, difficulty, num_questions=12)

        # Store session in database
        session_id = create_session(
            resume_filename=filename,
            resume_text=resume_text[:5000],  # Store first 5000 chars
            resume_data=resume_data,
            difficulty=difficulty,
            total_questions=len(questions_list)
        )

        # Save questions to DB
        question_ids = save_questions(session_id, questions_list)

        # Store session info in Flask session for quick access
        session['current_session_id'] = session_id
        session['question_index'] = 0
        session['question_ids'] = question_ids

        return jsonify({
            'success': True,
            'session_id': session_id,
            'candidate_name': resume_data.get('name', 'Candidate'),
            'difficulty': difficulty,
            'total_questions': len(questions_list),
            'skills_found': resume_data.get('skills', []) + resume_data.get('programming_languages', []),
            'redirect': url_for('interview', session_id=session_id)
        })

    except Exception as e:
        # Clean up file on error
        if os.path.exists(filepath):
            os.remove(filepath)
        print(f"Upload error: {e}")
        return jsonify({'error': f'Failed to process resume: {str(e)}'}), 500


# ═══════════════════════════════════════════════
# INTERVIEW SESSION
# ═══════════════════════════════════════════════

@app.route('/interview/<int:session_id>')
def interview(session_id):
    """Interview page for a specific session."""
    interview_session = get_session(session_id)

    if not interview_session:
        return redirect(url_for('index'))

    if interview_session['status'] == 'completed':
        return redirect(url_for('result', session_id=session_id))

    questions = get_session_questions(session_id)
    if not questions:
        return redirect(url_for('index'))

    # Get current question index from session
    current_index = session.get('question_index', 0)

    # Ensure question_ids are in session
    if 'question_ids' not in session or session.get('current_session_id') != session_id:
        session['current_session_id'] = session_id
        session['question_index'] = 0
        session['question_ids'] = [q['id'] for q in questions]

    return render_template(
        'interview.html',
        interview_session=interview_session,
        questions=questions,
        current_question_index=current_index,
        total_questions=len(questions)
    )


@app.route('/api/question/<int:session_id>/<int:index>')
def get_question_api(session_id, index):
    """API endpoint to get a specific question by index."""
    questions = get_session_questions(session_id)

    if index >= len(questions):
        return jsonify({'done': True, 'redirect': url_for('finalize_interview', session_id=session_id)})

    question = questions[index]
    return jsonify({
        'id': question['id'],
        'text': question['question_text'],
        'type': question['question_type'],
        'index': index,
        'total': len(questions),
        'is_followup': bool(question.get('is_followup', 0))
    })


@app.route('/api/submit-answer', methods=['POST'])
def submit_answer():
    """
    Submit an answer for a question, get AI evaluation,
    and optionally generate a follow-up question.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data.'}), 400

    session_id = data.get('session_id')
    question_id = data.get('question_id')
    answer_text = data.get('answer', '').strip()

    if not session_id or not question_id:
        return jsonify({'error': 'Missing session or question ID.'}), 400

    if not answer_text:
        return jsonify({'error': 'Answer cannot be empty.'}), 400

    # Get question and session info
    question = get_question(question_id)
    interview_session = get_session(session_id)

    if not question or not interview_session:
        return jsonify({'error': 'Session or question not found.'}), 404

    resume_data = interview_session.get('resume_data', {})
    difficulty = interview_session.get('difficulty', 'fresher')

    # Create brief resume context for evaluation
    skills = ', '.join(resume_data.get('skills', []) + resume_data.get('programming_languages', []))
    resume_context = f"Skills: {skills[:200]}"

    try:
        # Evaluate the answer with Gemini
        evaluation = evaluate_answer(
            question=question['question_text'],
            answer=answer_text,
            question_type=question['question_type'],
            resume_context=resume_context,
            difficulty=difficulty
        )

        # Save answer and evaluation to DB
        save_answer(question_id, session_id, answer_text, evaluation)

        # Update completed questions count
        questions = get_session_questions(session_id)
        answers = get_session_answers(session_id)
        update_session_completed_questions(session_id, len(answers))

        # Try to generate a follow-up question
        followup_text = None
        followup_id = None

        if evaluation.get('score', 10) < 9:  # Only generate if answer wasn't perfect
            try:
                followup_text = generate_followup_question(
                    question=question['question_text'],
                    answer=answer_text,
                    resume_context=resume_context
                )

                if followup_text:
                    # Save follow-up question to DB
                    next_order = len(questions) + 1
                    followup_id = save_followup_question(
                        session_id=session_id,
                        question_text=followup_text,
                        parent_id=question_id,
                        order_num=next_order
                    )
            except Exception as fe:
                print(f"Follow-up generation error (non-critical): {fe}")

        return jsonify({
            'success': True,
            'evaluation': {
                'score': evaluation.get('score', 0),
                'strengths': evaluation.get('strengths', []),
                'missing': evaluation.get('missing', []),
                'improved_answer': evaluation.get('improved_answer', ''),
                'brief_feedback': evaluation.get('brief_feedback', ''),
                'communication_score': evaluation.get('communication_score', 0),
                'confidence_score': evaluation.get('confidence_score', 0)
            },
            'followup': {
                'text': followup_text,
                'id': followup_id
            } if followup_text else None
        })

    except Exception as e:
        print(f"Answer submission error: {e}")
        return jsonify({'error': f'Evaluation failed: {str(e)}'}), 500


@app.route('/api/finalize/<int:session_id>', methods=['POST'])
def finalize_interview(session_id):
    """
    Finalize the interview, generate the full report, and mark session as completed.
    """
    interview_session = get_session(session_id)
    if not interview_session:
        return jsonify({'error': 'Session not found.'}), 404

    try:
        # Get all answers with evaluations
        answers = get_session_answers(session_id)

        if not answers:
            return jsonify({'error': 'No answers found. Please answer at least one question.'}), 400

        resume_data = interview_session.get('resume_data', {})

        # Generate comprehensive final report
        report_data = generate_final_report(
            session_data=interview_session,
            answers_with_evaluations=answers,
            resume_data=resume_data
        )

        # Save report to database
        save_report(session_id, report_data)

        # Mark session as completed
        update_session_status(session_id, 'completed')

        return jsonify({
            'success': True,
            'redirect': url_for('result', session_id=session_id)
        })

    except Exception as e:
        print(f"Finalization error: {e}")
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500


# ═══════════════════════════════════════════════
# RESULTS & REPORTS
# ═══════════════════════════════════════════════

@app.route('/result/<int:session_id>')
def result(session_id):
    """Display the final interview result and report."""
    interview_session = get_session(session_id)
    if not interview_session:
        return redirect(url_for('index'))

    report = get_report(session_id)
    answers = get_session_answers(session_id)
    questions = get_session_questions(session_id)

    return render_template(
        'result.html',
        interview_session=interview_session,
        report=report,
        answers=answers,
        questions=questions
    )


@app.route('/api/report-data/<int:session_id>')
def report_data_api(session_id):
    """API endpoint for fetching report data (used for chart rendering)."""
    report = get_report(session_id)
    if not report:
        return jsonify({'error': 'Report not found.'}), 404

    return jsonify({
        'overall_score': report.get('overall_score', 0),
        'technical_score': report.get('technical_score', 0),
        'project_score': report.get('project_score', 0),
        'communication_score': report.get('communication_score', 0),
        'confidence_score': report.get('confidence_score', 0),
        'hr_score': report.get('hr_score', 0),
        'strengths': report.get('strengths', []),
        'weaknesses': report.get('weaknesses', []),
        'recommendations': report.get('recommendations', [])
    })


# ═══════════════════════════════════════════════
# CLEANUP
# ═══════════════════════════════════════════════

@app.route('/api/cleanup-uploads', methods=['POST'])
def cleanup_uploads():
    """Remove old uploaded files (keep DB records). For maintenance."""
    try:
        upload_dir = app.config['UPLOAD_FOLDER']
        count = 0
        for f in os.listdir(upload_dir):
            if f != '.gitkeep':
                os.remove(os.path.join(upload_dir, f))
                count += 1
        return jsonify({'success': True, 'removed': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    print(f"[START] InterviewAI running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
