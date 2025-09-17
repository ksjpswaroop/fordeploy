import os, sys
print('CWD', os.getcwd())
print('Sys path start', sys.path[:5])
try:
    from app.main import app
    print('Imported app.main successfully')
except Exception as e:
    print('Import failed:', e)
    raise

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8011)
