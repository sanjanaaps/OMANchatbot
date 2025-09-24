#!/usr/bin/env python3
"""
Simple test to verify Flask is working
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '''
    <html>
    <head><title>Oman Central Bank - Test</title></head>
    <body>
        <h1>🎉 Success! Flask is working!</h1>
        <p>Your Oman Central Bank Document Analyzer is ready!</p>
        <p>Go back to the terminal and run: <code>python run_app.py</code></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("Starting simple Flask test...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
