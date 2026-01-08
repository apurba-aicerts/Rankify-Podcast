import asyncio
import logging
from typing import Optional

from schemas.podcast import PodcastScript
from prompts.podcast import PODCAST_SYSTEM_INSTRUCTION
from core.gemini_client import run_gemini_agent

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("podcast-generator")

# ------------------------------------------------------------------------------
# Core Podcast Generation Logic
# ------------------------------------------------------------------------------

async def generate_podcast_script(
    input_text: str,
    model: str = "gemini-3-pro-preview",
    temperature: float = 0.7
) -> Optional[PodcastScript]:
    """
    Generate a podcast-ready dialogue from raw input text.

    Args:
        input_text (str): Raw content to convert into a podcast conversation
        model (str): Gemini model name
        temperature (float): Creativity control

    Returns:
        PodcastScript | None: Validated podcast script or None on failure
    """
    logger.info("Starting podcast script generation")

    result = await run_gemini_agent(
        instruction=PODCAST_SYSTEM_INSTRUCTION,
        user_input=input_text,
        output_type=PodcastScript,
        model=model,
        temperature=temperature,
        retries=2
    )

    if result is None:
        logger.error("Podcast script generation failed")
    else:
        logger.info("Podcast script generated successfully")

    return result

# ------------------------------------------------------------------------------
# Pretty Printer (Human-Readable Output)
# ------------------------------------------------------------------------------

def print_podcast_script(script: PodcastScript) -> None:
    print("\n" + "=" * 80)
    print(f"🎧 TITLE: {script.title}\n")
    print(f"📝 DESCRIPTION:\n{script.description}")
    print("\n" + "-" * 80)

    for turn in script.dialogue:
        print(f"\n{turn.speaker}:")
        print(f"{turn.text}")

    print("\n" + "=" * 80 + "\n")

# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

async def main() -> None:
    print("\n🎙️  TEXT → PODCAST DIALOGUE GENERATOR\n")
    # print("Paste your input text below (press Enter twice to finish):\n")

    # # Multi-line input support
    # lines = []
    # while True:
    #     line = input()
    #     if line.strip() == "":
    #         break
    #     lines.append(line)

    # input_text = "\n".join(lines)
    input_text = """
Are you looking for an easy guide on how to start a blog?

The step-by-step guide on this page will show you how to create a blog in 20 minutes with just the most basic computer skills.

Ready to start? Click here to skip to Step #1 of the free guide and start building your blog now!

After completing this guide you will have a beautiful blog that is ready to share with the world.

This guide is made especially for beginners. I will walk you through each and every step, using plenty of pictures and videos to make it all perfectly clear.

If you get stuck or have questions at any point, simply send me a message and I will do my best to help you out.

How to start a blog for beginners 

My name is Scott Chow, and I am going to show you how to start blogging today. I have been building blogs and websites since 2002. In that time I have launched several of my own blogs, and helped hundreds of others do the same.

I know that starting a blog can seem overwhelming and intimidating. This free guide is all about blogging for beginners, and will teach you how to become a blogger with just the most basic computer skills. So whether you’re 8 or 88, you can create your own blog in 20 minutes.

I am not ashamed to admit that when I was first learning how to build a blog I made a ton of mistakes. You can benefit from more than a decade of my experience so that you don’t repeat these same mistakes when you make your own blog. I created this free guide so that a complete beginner can learn how to blog quickly and easily.

So, just how do you start a blog?

Learn how to create a blog in about 20 minutes following these steps:

How to Start a Blog in 6 Steps
Pick a blog name. Choose a descriptive name for your blog.
Get your blog online. Register your blog and get hosting.
Customize your blog. Choose a free blog design template and tweak it.
Write & publish your first post. Share your thoughts with the world. The fun part!
Promote your blog. Get more people to read your blog with the proper marketing.
Make money blogging. Choose from several options to monetize your blog.
"""

    if not input_text.strip():
        print("❌ No input provided. Exiting.")
        return

    script = await generate_podcast_script(input_text)

    if script:
        print(script)
        print_podcast_script(script)
    else:
        print("❌ Failed to generate podcast dialogue.")

# ------------------------------------------------------------------------------
# Run
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
