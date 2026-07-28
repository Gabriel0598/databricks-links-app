# Databricks Links Manager

A Flask web application for managing and organizing web links with search functionality, designed to run on Databricks Apps.

## Features

- 📝 **Add Links**: Save links with title, description, and URL
- 🔍 **Search**: Case-insensitive search across all fields
- ✏️ **Edit**: Update existing links inline
- 💾 **Persistent Storage**: All data stored in Databricks Unity Catalog
- 🎨 **Modern UI**: Clean, responsive design with animations

## Architecture

- **Frontend**: HTML/CSS with Jinja2 templates
- **Backend**: Flask (Python)
- **Database**: Databricks Unity Catalog (`workspace.bronze.links` table)
- **SQL Execution**: Databricks SQL Warehouse via WorkspaceClient SDK

## Files

- `app.py` - Main Flask application
- `app.yaml` - Databricks App configuration
- `requirements.txt` - Python dependencies

## Database Schema

```sql
CREATE TABLE workspace.bronze.links (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    title STRING NOT NULL,
    description STRING,
    url STRING NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## Deployment Options

### Option 1: Databricks Apps (Original Design)

1. Deploy to Databricks Apps
2. Configure SQL warehouse access
3. Grant Unity Catalog permissions

### Option 2: Alternative Python Hosting

This Flask app can run on any Python hosting platform:

- **Heroku**: Free tier available
- **Railway**: Modern platform with free tier
- **Render**: Free tier for web services
- **PythonAnywhere**: Free tier for Flask apps
- **Replit**: Quick deployment

**Note**: GitHub Pages **cannot** host this app as it only supports static files, not Python servers.

## Environment Requirements

- Python 3.8+
- Databricks workspace access
- SQL Warehouse for query execution
- Unity Catalog permissions:
  - `USE CATALOG` on `workspace`
  - `USE SCHEMA` on `workspace.bronze`
  - `SELECT, MODIFY` on `workspace.bronze.links`

## Security Notes

- SQL injection mitigation via quote escaping
- Input validation on all forms
- Server-side authentication via Databricks SDK

## Known Issues

- SQL Warehouse cold start can take 30-60 seconds on first request
- The app polls for statement completion (up to 60 seconds timeout)

## Future Improvements

- [ ] Pagination for search results
- [ ] Bulk import/export
- [ ] Tags/categories
- [ ] Favorite links
- [ ] Link validation
- [ ] Usage analytics

## License

MIT

## Author

Developed with Databricks Assistant