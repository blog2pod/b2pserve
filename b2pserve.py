import http.server
import socketserver
from pathlib import Path
import urllib.parse
import threading
import time
import subprocess
from dotenv import load_dotenv
import os
from music_tag import load_file

PORT = 8000
DIRECTORY = Path("completed").resolve()

# Load environment variables
load_dotenv()

base_url = os.getenv("BASEURL")
pod_title = os.getenv("POD_TITLE")
pod_description = os.getenv("POD_DESCRIPTION")
pod_image = os.getenv("POD_IMAGE")
pod_author = os.getenv("POD_AUTHOR")
pod_email = ""

class PodcastRequestHandler(http.server.SimpleHTTPRequestHandler):
    rss_feed_content = ""

    def do_GET(self):
        # Directly serve the RSS feed at both /rss.xml and the base URL
        if self.path in ["/rss.xml", "/"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/xml")  # Changed to text/xml
            self.send_header("Cache-Control", "no-store")  # Optionally to prevent caching issues
            self.end_headers()
            self.wfile.write(self.rss_feed_content.encode('utf-8'))
        else:
            requested_file = urllib.parse.unquote(self.path).lstrip('/')
            file_path = DIRECTORY / requested_file

            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.end_headers()

                with file_path.open('rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")

    @staticmethod
    def get_file_duration(file_path):
        """Use ffmpeg to get the duration of the MP3 file in HH:MM:SS format."""
        result = subprocess.run(
            ["ffmpeg", "-i", str(file_path), "-f", "null", "-"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
        )
        for line in result.stderr.splitlines():
            if "Duration" in line:
                duration = line.split(",")[0].split("Duration:")[1].strip()
                return duration.split('.')[0]  # Format to HH:MM:SS
        return "00:00:00"  # Default duration if not found

    @staticmethod
    def generate_rss_feed():
        rss_items = ""

        for file in DIRECTORY.glob("*.mp3"):
            episode_url = f"{base_url}{urllib.parse.quote(file.name)}"
            file_size = file.stat().st_size
            pub_date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(file.stat().st_mtime))
            duration = PodcastRequestHandler.get_file_duration(file)
            audio_file = load_file(file)
            artist = audio_file['artist']

            rss_items += f"""
            <item>
                <title><![CDATA[{file.stem}]]></title>
                <description><![CDATA[{artist}]]></description>
                <link>{episode_url}</link>
                <guid isPermaLink="false">{episode_url}</guid>
                <dc:creator><![CDATA[codefruit]]></dc:creator>
                <enclosure url="{episode_url}" length="{file_size}" type="audio/mpeg"/>
                <itunes:author>codefruit</itunes:author>
                <itunes:duration>{duration}</itunes:duration>
                <itunes:summary><![CDATA[{artist}]]></itunes:summary>
                <itunes:explicit>false</itunes:explicit>
                <pubDate>{pub_date}</pubDate>
            </item>"""

        rss_feed = f"""
        <rss xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:content="http://purl.org/rss/1.0/modules/content/" 
            xmlns:atom="http://www.w3.org/2005/Atom" 
            xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
            xmlns:psc="http://podlove.org/simple-chapters" 
            xmlns:podcast="https://podcastindex.org/namespace/1.0" 
            xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0" 
            version="2.0">
            <channel>
                <title><![CDATA[{pod_title}]]></title>
                <description><![CDATA[{pod_description}]]></description>
                <link>{base_url}rss.xml</link>
                <itunes:image href="{pod_image}"/>
                <image>
                    <url>{pod_image}</url>
                    <title>{pod_title}</title>
                    <link>{base_url}rss.xml</link>
                </image>
                <generator>CustomPythonPodcastGenerator</generator>
                <lastBuildDate>{time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())}</lastBuildDate>
                <atom:link href="{base_url}rss.xml" rel="self" type="application/rss+xml"/>
                <language>English</language>
                <itunes:author>{pod_author}</itunes:author>
                <itunes:summary><![CDATA[AI generated audio for articles that I don't have time to read ...]]></itunes:summary>
                <itunes:type>episodic</itunes:type>
                <itunes:explicit>false</itunes:explicit>
                <itunes:block>yes</itunes:block>
                <itunes:owner>
                    <itunes:name>{pod_author}</itunes:name>
                    <itunes:email>{pod_email}</itunes:email>
                </itunes:owner>
                <googleplay:block>yes</googleplay:block>
                {rss_items}
            </channel>
        </rss>"""

        return rss_feed


def update_rss_feed(handler):
    while True:
        print("Updating RSS feed...")
        handler.rss_feed_content = handler.generate_rss_feed()
        time.sleep(60)

handler = PodcastRequestHandler

# Start the RSS feed updating thread
rss_thread = threading.Thread(target=update_rss_feed, args=(handler,), daemon=True)
rss_thread.start()

with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Serving podcast feed at {base_url}")
    httpd.serve_forever()
    
