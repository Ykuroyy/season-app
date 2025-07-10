#!/usr/bin/env python3
"""
データベース初期化スクリプト
Renderデプロイ時に実行される
"""

from app import app, db

def init_database():
    """データベースとテーブルを初期化"""
    with app.app_context():
        db.create_all()
        print("✅ データベーステーブルが正常に作成されました")
        print("📊 テーブル: season_activity")

if __name__ == "__main__":
    init_database() 