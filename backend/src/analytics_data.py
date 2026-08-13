import json
import db

def main():
    db.init_db()
    summary = db.get_analytics_summary()
    print(json.dumps(summary))

if __name__ == "__main__":
    main()
