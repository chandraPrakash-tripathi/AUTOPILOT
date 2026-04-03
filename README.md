1) database setup
    a) winget install -e --id SQLite.SQLite
    b) after this a) part installation we can see the sqlite3 databse tables and other stuff using the cli (>> sqlite3 autopilot.db)
    c)



 Token saved to youtube_token.json
✅ YouTube connected!
   Channel : AI HEALTH VERSE
   ID      : UC153w1aG2l0_HcCVGpPNFwg



-----------------------------------------------------------------------------
 PS E:\1.Workspace\3.PROJECTS\1.AI-ML\AUTOPILOT> streamlit run dashboard/app.py

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.29.123:8501


🚀 Found 1 approved video(s) to upload.

==================================================
📹 Processing: Video (15).mp4
🎯 Platform  : both
📝 Caption   : #health #nochaiemptystomach...
==================================================

⬇️  Downloading from Google Drive...
⬇️  Downloading Video (15).mp4: 100%
✅ Downloaded to: downloads\Video (15).mp4

📸 Starting Instagram Reel upload: Video (15).mp4
📤 Step 1/3: Creating Instagram Reel container...
Instagram container error: {'message': "Unsupported post request. Object with ID '1955274411750298' does not exist, cannot be loaded due to missing permissions, or does not support this operation. Please read the Graph API documentation at https://developers.facebook.com/docs/graph-api", 'type': 'GraphMethodException', 'code': 100, 'error_subcode': 33, 'fbtrace_id': 'ARZb88dtUTQxLLqcDmNs0kV'}
❌ Container creation failed: Unsupported post request. Object with ID '1955274411750298' does not exist, cannot be loaded due to missing permissions, or does not support this operation. Please read the Graph API documentation at https://developers.facebook.com/docs/graph-api
⚠️  Instagram upload failed — continuing...

▶️  Starting YouTube Short upload: Video (15).mp4
🔄 Refreshing YouTube token...
✅ Token saved to youtube_token.json
📤 Uploading to YouTube...
   Upload progress: 53%
✅ YouTube Short uploaded!
   Video ID : ePMw-b05X9A
   URL      : https://youtube.com/shorts/ePMw-b05X9A
▶️  YouTube video ID : ePMw-b05X9A

✅ Marked as uploaded in DB.
🗑️  Cleaned up: downloads\Video (15).mp4