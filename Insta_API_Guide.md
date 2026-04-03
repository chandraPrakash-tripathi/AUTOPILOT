# 📸 Instagram Graph API Setup Guide (Reels Automation Ready)

This guide walks you through setting up the **Instagram Graph API** from scratch and generating a **long-lived access token** for automation (e.g., posting reels).

---

# 🚀 Overview

By the end of this setup, you will have:

* ✅ Meta Developer App
* ✅ Instagram Business/Creator Account
* ✅ Facebook Page linked to Instagram
* ✅ Valid Access Token
* ✅ Long-Lived Token (60 days)
* ✅ Instagram Account ID

---

# 🧩 Step 1 — Create Meta Developer App

1. Go to: https://developers.facebook.com/apps
2. Click **Create App**
3. Select:

   * **Other → Business**
4. Fill:

   * App Name → `Autopilot Reels`
   * Email → your email
5. Click **Create App**

---

# 📦 Step 2 — Add Instagram Graph API

1. Open your app dashboard
2. Go to:

   * **Use Cases → Manage messaging & content on Instagram**
3. Click:

   * **Customize / Continue Setup**

---

# 🔗 Step 3 — Setup Instagram & Facebook

## 3.1 Create Instagram Account

* Create a new account (recommended)
* Convert to:

  * **Professional Account → Creator**

---

## 3.2 Create Facebook Page

* Open Facebook → Pages → Create New Page
* Name: `Autopilot Reels`
* Category: `Digital Creator`

---

## 3.3 Link Instagram to Facebook Page

* Instagram → Settings → Accounts Center
* Add Facebook account
* Link Instagram to your Facebook Page

---

## 3.4 Add Instagram Tester

1. Go to:

   * **Use Cases → Instagram → Roles**
2. Click:

   * **Add Instagram Tester**
3. Enter your username

---

## 3.5 Accept Tester Invite

On Instagram:

* Settings → Accounts Center / Apps & Websites
* Open:

  * **Tester Invites**
* Click **Accept**

---

# 🔑 Step 4 — Generate Access Token

## Use Graph API Explorer:

👉 https://developers.facebook.com/tools/explorer

### Steps:

1. Select your app
2. Click **Generate Access Token**
3. Add permissions:

```
instagram_basic
instagram_content_publish
pages_read_engagement
pages_show_list
```

4. Continue:

   * Select Facebook account
   * Select Page
   * Select Instagram account
   * Allow all permissions

---

## ✅ Test Token

```
https://graph.facebook.com/v19.0/me?access_token=YOUR_TOKEN
```

Expected:

```
{
  "id": "...",
  "name": "..."
}
```

---

# 🧠 Step 5 — Get Instagram Account ID

## 1. Get Page ID

```
https://graph.facebook.com/v19.0/me/accounts?access_token=YOUR_TOKEN
```

Response:

```
{
  "data": [
    {
      "id": "PAGE_ID",
      "name": "Your Page"
    }
  ]
}
```

---

## 2. Get Instagram Account ID

```
https://graph.facebook.com/v19.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN
```

Response:

```
{
  "instagram_business_account": {
    "id": "INSTAGRAM_ACCOUNT_ID"
  }
}
```

---

# 🔐 Step 6 — Convert to Long-Lived Token

## Endpoint:

```
https://graph.facebook.com/v19.0/oauth/access_token
```

## Params:

| Key               | Value             |
| ----------------- | ----------------- |
| grant_type        | fb_exchange_token |
| client_id         | YOUR_APP_ID       |
| client_secret     | YOUR_APP_SECRET   |
| fb_exchange_token | YOUR_SHORT_TOKEN  |

---

## ✅ Response:

```
{
  "access_token": "LONG_TOKEN",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

---

# 📁 Step 7 — Save Credentials

Create `.env` file:

```
INSTAGRAM_ACCOUNT_ID=your_instagram_id
INSTAGRAM_ACCESS_TOKEN=your_long_token
```

---

# ⚠️ Common Errors & Fixes

### ❌ Invalid OAuth Token

* Token not copied correctly
* Expired token
* Wrong token type

---

### ❌ No Instagram Account Found

* Instagram not linked to Facebook Page
* Not a Professional account

---

### ❌ Permission Denied

* Tester invite not accepted
* Missing permissions

---

# 🔥 Final Architecture

```
Instagram → Facebook Page → Meta App → Graph API → Your Code
```

---

# 🚀 Next Steps

Now you can:

* ✅ Upload Instagram Reels via API
* ✅ Automate posting
* ✅ Build content pipelines

---

# 🎯 Recommended Next

* Python script for reel upload
* n8n automation (3 posts/day)

---

# 🔒 Security Notes

* Keep tokens private
* Do not commit `.env` to GitHub
* Refresh token every 60 days

---

# 🎉 You’re Done!

You now have a **fully working Instagram API setup** ready for automation 🚀
