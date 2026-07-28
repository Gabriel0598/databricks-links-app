from flask import Flask, request, render_template_string, redirect, url_for
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
import logging
import os
import time

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

# Database configuration
CATALOG = "workspace"
SCHEMA = "bronze"
TABLE = "links"
FULL_TABLE_NAME = f"{CATALOG}.{SCHEMA}.{TABLE}"
SQL_WAREHOUSE_ID = "3d01a61a0711dab5"  # Serverless Starter Warehouse

# Initialize Databricks client
w = WorkspaceClient()

# Helper function to execute SQL
def execute_sql(sql_query, wait_for_result=True):
    try:
        print(f"[DEBUG] Executing SQL: {sql_query[:100]}...")
        print(f"[DEBUG] Warehouse ID: {SQL_WAREHOUSE_ID}")
        
        # Execute SQL statement
        result = w.statement_execution.execute_statement(
            statement=sql_query,
            warehouse_id=SQL_WAREHOUSE_ID,
            catalog=CATALOG,
            schema=SCHEMA,
            wait_timeout="50s"  # Increased timeout for warehouse startup
        )
        
        statement_id = result.statement_id
        print(f"[DEBUG] Statement ID: {statement_id}")
        print(f"[DEBUG] Initial status: {result.status.state if result.status else 'no status'}")
        
        # Poll until statement completes (if PENDING/RUNNING)
        max_polls = 60  # Max 60 seconds
        poll_count = 0
        while result.status and result.status.state in [StatementState.PENDING, StatementState.RUNNING]:
            if poll_count >= max_polls:
                raise Exception(f"Statement timed out after {max_polls} seconds")
            time.sleep(1)
            poll_count += 1
            result = w.statement_execution.get_statement(statement_id)
            print(f"[DEBUG] Poll {poll_count}: {result.status.state}")
        
        print(f"[DEBUG] Final statement status: {result.status.state if result.status else 'no status'}")
        
        # Check for errors
        if result.status and result.status.state == StatementState.FAILED:
            error_msg = result.status.error.message if result.status.error else 'Unknown error'
            print(f"[ERROR] SQL execution failed: {error_msg}")
            raise Exception(f"SQL execution failed: {error_msg}")
        
        if wait_for_result and result.result:
            # Convert result to list of row objects
            if result.result.data_array:
                from datetime import datetime
                columns = [col.name for col in result.manifest.schema.columns] if result.manifest and result.manifest.schema else []
                rows = []
                for row_data in result.result.data_array:
                    row_dict = {}
                    for idx, value in enumerate(row_data):
                        if idx < len(columns):
                            col_name = columns[idx]
                            # Parse timestamp strings to datetime objects
                            if value and isinstance(value, str) and ('created_at' in col_name or 'updated_at' in col_name):
                                try:
                                    row_dict[col_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                except:
                                    row_dict[col_name] = value
                            else:
                                row_dict[col_name] = value
                    # Create a simple object to access via dot notation
                    row_obj = type('Row', (), row_dict)
                    rows.append(row_obj)
                print(f"[DEBUG] Returning {len(rows)} rows")
                return rows
            return []
        
        print(f"[DEBUG] SQL executed successfully")
        return None
    except Exception as e:
        print(f"[ERROR] SQL execution error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

# Initialize database table
def init_db():
    try:
        # Create table if it doesn't exist (schema already exists)
        execute_sql(f"""
            CREATE TABLE IF NOT EXISTS {FULL_TABLE_NAME} (
                id BIGINT GENERATED ALWAYS AS IDENTITY,
                title STRING NOT NULL,
                description STRING,
                url STRING NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """, wait_for_result=False)
        print(f"✓ Database initialized: {FULL_TABLE_NAME}")
    except Exception as e:
        print(f"⚠ Database initialization error: {e}")

# Initialize on startup
init_db()

# HTML Templates
FORM_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Link Manager - Add Link</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               min-height: 100vh; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; }
        .card { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: #666; margin-bottom: 25px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; font-size: 14px; }
        input, textarea { width: 100%; padding: 12px; border: 2px solid #e0e0e0; 
                         border-radius: 8px; font-size: 14px; transition: border 0.3s; }
        input:focus, textarea:focus { outline: none; border-color: #667eea; }
        textarea { resize: vertical; min-height: 80px; font-family: inherit; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
               padding: 14px 28px; border: none; border-radius: 8px; cursor: pointer; 
               font-size: 16px; font-weight: 600; width: 100%; transition: transform 0.2s, box-shadow 0.2s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
        .btn:active { transform: translateY(0); }
        .nav-link { display: inline-block; margin-top: 20px; color: white; 
                   text-decoration: none; font-size: 14px; font-weight: 500; 
                   padding: 10px 20px; background: rgba(255,255,255,0.2); 
                   border-radius: 6px; transition: background 0.3s; }
        .nav-link:hover { background: rgba(255,255,255,0.3); }
        .success { background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                  color: white; padding: 16px 20px; border-radius: 8px; 
                  margin-bottom: 20px; text-align: center; font-weight: 600; 
                  font-size: 16px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                  animation: slideDown 0.4s ease-out; }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>📝 Add New Link</h1>
            <p class="subtitle">Save your favorite links with descriptions</p>
            
            {% if success %}
            <div class="success">🎉 Success! Your link has been saved.</div>
            {% endif %}
            
            <form method="POST" action="/">
                <div class="form-group">
                    <label for="title">Title *</label>
                    <input type="text" id="title" name="title" required placeholder="Enter link title">
                </div>
                
                <div class="form-group">
                    <label for="description">Description</label>
                    <textarea id="description" name="description" placeholder="Add a description (optional)"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="url">URL *</label>
                    <input type="url" id="url" name="url" required placeholder="https://example.com">
                </div>
                
                <button type="submit" class="btn">Save Link</button>
            </form>
        </div>
        <a href="/search" class="nav-link">🔍 Search Links</a>
    </div>
</body>
</html>
'''

SEARCH_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Link Manager - Search</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               min-height: 100vh; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        .card { background: white; border-radius: 12px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); margin-bottom: 20px; }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: #666; margin-bottom: 25px; font-size: 14px; }
        .search-box { display: flex; gap: 10px; margin-bottom: 25px; }
        .search-box input { flex: 1; padding: 12px; border: 2px solid #e0e0e0; 
                           border-radius: 8px; font-size: 14px; }
        .search-box input:focus { outline: none; border-color: #667eea; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
               padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; 
               font-size: 14px; font-weight: 600; transition: transform 0.2s, box-shadow 0.2s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
        .btn-small { padding: 8px 16px; font-size: 13px; margin-right: 8px; }
        .btn-secondary { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .result-item { border: 2px solid #f0f0f0; border-radius: 8px; padding: 20px; 
                      margin-bottom: 15px; transition: border-color 0.3s, box-shadow 0.3s; }
        .result-item:hover { border-color: #667eea; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1); }
        .result-title { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px; }
        .result-desc { color: #666; margin-bottom: 10px; font-size: 14px; line-height: 1.5; }
        .result-url { color: #667eea; font-size: 13px; margin-bottom: 12px; word-break: break-all; }
        .result-meta { color: #999; font-size: 12px; margin-bottom: 12px; }
        .nav-link { display: inline-block; margin-top: 10px; color: white; 
                   text-decoration: none; font-size: 14px; font-weight: 500; 
                   padding: 10px 20px; background: rgba(255,255,255,0.2); 
                   border-radius: 6px; transition: background 0.3s; }
        .nav-link:hover { background: rgba(255,255,255,0.3); }
        .no-results { text-align: center; color: #999; padding: 40px; font-size: 16px; }
        .edit-form { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; display: none; }
        .edit-form input, .edit-form textarea { width: 100%; padding: 10px; margin-bottom: 10px; 
                                                border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .edit-form textarea { resize: vertical; min-height: 60px; font-family: inherit; }
        .success { background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                  color: white; padding: 16px 20px; border-radius: 8px; 
                  margin-bottom: 20px; text-align: center; font-weight: 600; 
                  font-size: 16px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                  animation: slideDown 0.4s ease-out; }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
    <script>
        function toggleEdit(id) {
            const form = document.getElementById('edit-' + id);
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔍 Search Links</h1>
            <p class="subtitle">Find your saved links by title, description, or URL</p>
            
            {% if updated %}
            <div class="success">✓ Link updated successfully!</div>
            {% endif %}
            
            <form method="GET" action="/search" class="search-box">
                <input type="text" name="q" value="{{ query }}" placeholder="Search... (e.g., 'games')">
                <button type="submit" class="btn">Search</button>
            </form>
            
            {% if results %}
                {% for row in results %}
                <div class="result-item">
                    <div class="result-title">{{ row.title }}</div>
                    {% if row.description %}
                    <div class="result-desc">{{ row.description }}</div>
                    {% endif %}
                    <div class="result-url">🔗 {{ row.url }}</div>
                    <div class="result-meta">Added: {{ row.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                    
                    <a href="{{ row.url }}" target="_blank" class="btn btn-small">Open URL</a>
                    <button onclick="toggleEdit({{ row.id }})" class="btn btn-small btn-secondary">Edit</button>
                    
                    <div id="edit-{{ row.id }}" class="edit-form">
                        <form method="POST" action="/update/{{ row.id }}">
                            <input type="text" name="title" value="{{ row.title }}" required placeholder="Title">
                            <textarea name="description" placeholder="Description">{{ row.description or '' }}</textarea>
                            <input type="url" name="url" value="{{ row.url }}" required placeholder="URL">
                            <button type="submit" class="btn btn-small">Save Changes</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% elif query %}
                <div class="no-results">No results found for "{{ query }}"</div>
            {% else %}
                <div class="no-results">Enter a search term to find links</div>
            {% endif %}
        </div>
        <a href="/" class="nav-link">📝 Add New Link</a>
    </div>
</body>
</html>
'''

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    success = False
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        url = request.form.get('url', '').strip()
        
        if title and url:
            try:
                # Escape single quotes to prevent SQL injection
                title_escaped = title.replace("'", "''")
                description_escaped = description.replace("'", "''")
                url_escaped = url.replace("'", "''")
                
                execute_sql(f"""
                    INSERT INTO {FULL_TABLE_NAME} (title, description, url, created_at, updated_at)
                    VALUES ('{title_escaped}', '{description_escaped}', '{url_escaped}', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
                """, wait_for_result=False)  # INSERT doesn't return rows
                print(f"[SUCCESS] Link inserted: {title}")
                success = True
            except Exception as e:
                print(f"[ERROR] Insert error: {e}")
                success = False
    
    return render_template_string(FORM_TEMPLATE, success=success)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    results = []
    updated = request.args.get('updated') == '1'
    
    if query:
        try:
            # Escape single quotes for SQL LIKE
            query_escaped = query.replace("'", "''")
            
            # Case-insensitive LIKE search across all fields
            results = execute_sql(f"""
                SELECT id, title, description, url, created_at, updated_at
                FROM {FULL_TABLE_NAME}
                WHERE LOWER(title) LIKE LOWER('%{query_escaped}%')
                   OR LOWER(description) LIKE LOWER('%{query_escaped}%')
                   OR LOWER(url) LIKE LOWER('%{query_escaped}%')
                ORDER BY created_at DESC
            """)
            if results is None:
                results = []
        except Exception as e:
            print(f"Search error: {e}")
            results = []
    
    return render_template_string(SEARCH_TEMPLATE, query=query, results=results, updated=updated)

@app.route('/update/<int:link_id>', methods=['POST'])
def update(link_id):
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    url = request.form.get('url', '').strip()
    
    if title and url:
        try:
            # Escape single quotes to prevent SQL injection
            title_escaped = title.replace("'", "''")
            description_escaped = description.replace("'", "''")
            url_escaped = url.replace("'", "''")
            
            execute_sql(f"""
                UPDATE {FULL_TABLE_NAME}
                SET title = '{title_escaped}',
                    description = '{description_escaped}',
                    url = '{url_escaped}',
                    updated_at = CURRENT_TIMESTAMP()
                WHERE id = {link_id}
            """, wait_for_result=False)
        except Exception as e:
            print(f"Update error: {e}")
    
    return redirect(url_for('search', q=request.args.get('q', ''), updated=1))

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', 8000))
    app.run(debug=True, host=host, port=port)