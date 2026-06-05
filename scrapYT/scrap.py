"""
YouTube Comment Scraper
GEMASTIK - Analisis Stance Kekerasan Seksual
Tim: Raihan, Azka, Yuma

Cara pakai:
1. pip install google-api-python-client pandas
2. Isi API_KEY dan TARGET_VIDEOS di bawah
3. Jalankan: python3 youtube_scraper.py
4. Hasil tersimpan di youtube_comments.csv

Cara ambil Video ID:
  URL: https://www.youtube.com/watch?v=ABC123xyz
  Video ID = ABC123xyz
"""

from googleapiclient.discovery import build
import pandas as pd
import time
import os

# ============================================================
# KONFIGURASI — Edit bagian ini
# ============================================================

API_KEY = "AIzaSyAKRHVAaDsIzDyZAiP2MovwSqRxL8s_Vzo"

# Video ID YouTube yang mau di-scrape komentarnya
# Cari video berita kekerasan seksual di channel berita besar
TARGET_VIDEOS = [
    # Contoh format: "ABC123xyz"
    # Rekomendasi cari di: Kompas TV, CNN Indonesia, Metro TV, detikcom
    # Keyword pencarian di YouTube:
    #   "kekerasan seksual mahasiswa"
    #   "pelecehan seksual kampus"
    #   "kasus kekerasan seksual viral"
    #   "kasus FH UI pelecehan"
    "t8nioXPX060",
    "5cnB4fU-M7I",
    "5H1OXFi7dPo",
    "MD760S8PvPs",
    "vZhqp6UBvRk",
    "I6gSIUauNPs",
]

# Output
OUTPUT_CSV  = "youtube_comments.csv"

# Maksimal komentar per video
MAX_COMMENTS_PER_VIDEO = 1000

# ============================================================
# SCRIPT UTAMA
# ============================================================

def get_video_info(youtube, video_id):
    """Ambil info dasar video."""
    try:
        response = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        ).execute()

        if not response["items"]:
            return None

        item = response["items"][0]
        return {
            "video_id"   : video_id,
            "title"      : item["snippet"]["title"],
            "channel"    : item["snippet"]["channelTitle"],
            "date"       : item["snippet"]["publishedAt"],
            "views"      : item["statistics"].get("viewCount", 0),
            "likes"      : item["statistics"].get("likeCount", 0),
            "url"        : f"https://www.youtube.com/watch?v={video_id}",
        }
    except Exception as e:
        print(f"    [!] Gagal ambil info video: {e}")
        return None


def scrape_comments(youtube, video_id, video_info, max_comments=500):
    """Scrape komentar dari satu video."""
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_comments:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance"
            )
            response = request.execute()

            for item in response.get("items", []):
                # Komentar utama
                top = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "video_id"      : video_id,
                    "video_title"   : video_info["title"][:80] if video_info else "",
                    "video_channel" : video_info["channel"] if video_info else "",
                    "video_date"    : video_info["date"] if video_info else "",
                    "comment_id"    : item["snippet"]["topLevelComment"]["id"],
                    "comment_text"  : top["textDisplay"],
                    "comment_likes" : top["likeCount"],
                    "comment_date"  : top["publishedAt"],
                    "is_reply"      : False,
                    "stance"        : "",  # diisi manual saat anotasi
                })

                # Replies
                if "replies" in item:
                    for reply in item["replies"]["comments"]:
                        rsnip = reply["snippet"]
                        comments.append({
                            "video_id"      : video_id,
                            "video_title"   : video_info["title"][:80] if video_info else "",
                            "video_channel" : video_info["channel"] if video_info else "",
                            "video_date"    : video_info["date"] if video_info else "",
                            "comment_id"    : reply["id"],
                            "comment_text"  : rsnip["textDisplay"],
                            "comment_likes" : rsnip["likeCount"],
                            "comment_date"  : rsnip["publishedAt"],
                            "is_reply"      : True,
                            "stance"        : "",
                        })

                if len(comments) >= max_comments:
                    break

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(0.5)

    except Exception as e:
        print(f"    [!] Error scraping komentar: {e}")

    return comments


def filter_noise(df):
    """Filter komentar yang tidak informatif untuk anotasi stance."""
    original = len(df)

    # Hapus kosong
    df = df[df["comment_text"].notna()]
    df = df[df["comment_text"].str.strip() != ""]

    # Hapus terlalu pendek
    df = df[df["comment_text"].str.len() >= 10]

    # Hapus yang hanya emoji/simbol
    df = df[df["comment_text"].str.contains(
        r"[a-zA-Z\u00C0-\u024F\u0100-\u017E\u0600-\u06FF]",
        regex=True, na=False
    )]

    # Hapus duplikat
    df = df.drop_duplicates(subset=["comment_text"])

    print(f"\n[Filter] {original} → {len(df)} komentar ({original - len(df)} noise dihapus)")
    return df


def main():
    print("=" * 55)
    print("YouTube Scraper — GEMASTIK Data Mining")
    print("=" * 55)

    if not TARGET_VIDEOS:
        print("\n[!] TARGET_VIDEOS masih kosong!")
        print("\nCara isi:")
        print("  1. Buka YouTube, search 'kekerasan seksual kampus'")
        print("  2. Buka video berita yang relevan")
        print("  3. Copy Video ID dari URL:")
        print("     https://www.youtube.com/watch?v=ABC123xyz")
        print("                                      ↑ ini Video ID-nya")
        print("  4. Paste ke TARGET_VIDEOS di script ini")
        print("\nRekomendasi channel:")
        print("  Kompas TV, CNN Indonesia, Metro TV, detikcom, Tribunnews")
        return

    if API_KEY == "PASTE_API_KEY_KALIAN_DI_SINI":
        print("\n[!] API_KEY belum diisi!")
        print("    Isi API_KEY di bagian KONFIGURASI script ini")
        return

    # Inisialisasi YouTube API
    youtube = build("youtube", "v3", developerKey=API_KEY)
    all_comments = []

    for i, video_id in enumerate(TARGET_VIDEOS):
        print(f"\n[{i+1}/{len(TARGET_VIDEOS)}] Scraping video: https://www.youtube.com/watch?v={video_id}")

        # Ambil info video
        video_info = get_video_info(youtube, video_id)
        if video_info:
            print(f"    Judul   : {video_info['title'][:70]}")
            print(f"    Channel : {video_info['channel']}")
            print(f"    Views   : {int(video_info['views']):,}")

        # Scrape komentar
        comments = scrape_comments(youtube, video_id, video_info, MAX_COMMENTS_PER_VIDEO)
        print(f"    [✓] {len(comments)} komentar berhasil di-scrape")
        all_comments.extend(comments)

        # Delay antar video
        if i < len(TARGET_VIDEOS) - 1:
            print("    [~] Menunggu 2 detik...")
            time.sleep(2)

    if not all_comments:
        print("\n[!] Tidak ada data yang berhasil di-scrape.")
        return

    # Simpan & filter
    df = pd.DataFrame(all_comments)
    df_clean = filter_noise(df.copy())
    df_clean.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # Ringkasan
    print(f"\n{'='*55}")
    print(f"RINGKASAN")
    print(f"{'='*55}")
    print(f"Total video      : {df['video_id'].nunique()}")
    print(f"Total komentar   : {len(df)}")
    print(f"Setelah filter   : {len(df_clean)}")
    print(f"File output      : {OUTPUT_CSV}")
    print(f"{'='*55}")
    print(f"\n[✓] Selesai! Buka {OUTPUT_CSV} untuk mulai anotasi.")


if __name__ == "__main__":
    main()