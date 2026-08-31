#!/usr/bin/env python3
"""
Simple Web Interface for Job Search
"""

from flask import Flask, render_template, request, jsonify
from simple_job_search import SimpleJobSearch
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('simple_search.html')

@app.route('/search', methods=['POST'])
def search_jobs():
    try:
        data = request.json
        job_title = data.get('job_title', '').strip()
        location = data.get('location', 'India').strip()
        
        if not job_title:
            return jsonify({'error': 'Job title is required'}), 400
        
        # Search jobs
        searcher = SimpleJobSearch()
        jobs = searcher.search_jobs(job_title, location)
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'count': len(jobs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)