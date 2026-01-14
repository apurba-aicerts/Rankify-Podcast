import asyncio
import logging
from typing import Optional

from schemas.podcast import PodcastScript
from prompts.podcast import podcast_system_instruction
from core.gemini_client import run_gemini_agent, build_speaker_voice_mapping
from audio.google_tts import MultiSpeakerTTS
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
    speaker_voices: list[str],
    num_speakers: int = 2,
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
        instruction=podcast_system_instruction(num_speakers,
                                               speaker_voices),
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
From Mind to Machine: The Rise of Manus AI as a Fully
Autonomous Digital Agent
Minjie Shen1, Yanshu Li2, Lulu Chen1, and Qikai Yang3
1Department of Electrical and Computer Engineering, Virginia Tech
2Department of Computer Science, Brown University
3Department of Computer Science, University of Illinois at Urbana-Champaign
arXiv:2505.02024v2  [cs.AI]  20 Jul 2025
Abstract
Manus AI is a general-purpose AI agent introduced in early 2025 as a breakthrough in au
tonomous artificial intelligence. Developed by the Chinese startup Monica.im, Manus is designed to
bridge the gap between ”mind” and ”hand”– it not only thinks and plans like a large language model,
but also executes complex tasks end-to-end to deliver tangible results. This paper provides a com
prehensive overview of Manus AI, examining its underlying technical architecture, its wide-ranging
applications across industries (including healthcare, finance, manufacturing, robotics, gaming, and
more), as well as its advantages, limitations, and future prospects. Ultimately, Manus AI is posi
tioned as an early glimpse into the future of AI– one where intelligent agents could revolutionize work
and daily life by turning high-level intentions into actionable outcomes, auguring a new paradigm of
human-AI collaboration.
1 Introduction
Recent years have witnessed tremendous breakthroughs in artificial intelligence (AI), from the rise of
deep neural networks to large language models that can converse and solve complex problems. Models
like OpenAI’s GPT-4 [1] have demonstrated unprecedented language understanding, yet such systems
typically operate as assistants that respond to queries rather than autonomously acting on tasks. The
next evolution in AI is the development of general-purpose AI agents that can bridge the gap between
decision-making and action. Manus AI is a prominent new example, described as one of the world’s first
truly autonomous AI agents capable of “thinking” and executing tasks much like a human assistant [2].
Manus AI, developed by the Chinese startup Monica in 2025, has quickly drawn global attention for
its ability to perform a wide array of real-world jobs with minimal human guidance. Unlike traditional
chatbots that strictly provide information or suggestions, Manus can plan solutions, invoke tools, and
carry out multi-step procedures on its own [3]. For example, rather than just giving travel advice, Manus
can autonomously plan an entire trip itinerary, gather relevant information from the web, and present a
f
inalized plan to the user, all without step-by-step prompts [3]. This agent-centric approach represents
a significant leap in AI capabilities and has fueled speculation that systems like Manus herald the next
stage in AI evolution toward artificial general intelligence (AGI).
In benchmark evaluations for general AI agents, Manus AI has reportedly achieved state-of-the-art
results. On the GAIA test—a comprehensive benchmark assessing an AI’s ability to reason, use tools,
and automate real-world tasks—Manus outperformed leading models including OpenAI’s GPT-4 [4]. In
fact, early reports suggest Manus exceeded the previous GAIA leaderboard champion’s score of 65%,
setting a new performance record [4]. Such achievements underscore the importance of Manus AI as a
breakthrough system in the competitive landscape of AI.
This paper provides a detailed examination of Manus AI. Section 2 explains how Manus AI works,
delving into its model architecture, core algorithms, training process, and unique features. Section
3 explores Manus AI’s applications across various industries—ranging from healthcare and finance to
robotics and education—illustrating its versatility. In Section 4, we compare Manus AI with other
cutting-edge AI technologies (including offerings from OpenAI, Google DeepMind, and Anthropic) to
analyze how Manus stands out. Section 5 discusses the strengths of Manus AI as well as its limitations
and ongoing challenges. Section 6 considers future prospects for Manus AI and its broader implications
"""

    if not input_text.strip():
        print("❌ No input provided. Exiting.")
        return

    selected_voice = ["kore", "puck"]
    script = await generate_podcast_script(input_text=input_text, 
                                           speaker_voices=selected_voice,
                                           num_speakers=2)

    print("✅ Podcast script generated successfully.")

    print(script)
    print(f"Speakers: {[speaker.name for speaker in script.speakers]}")
    # import json
    # from pathlib import Path

    # OUTPUT_JSON = Path("netcom_podcast_script.json")

    # script_json = script.dict()

    # with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    #     json.dump(script_json, f, indent=2, ensure_ascii=False)

    # print(f"✅ Podcast script saved to {OUTPUT_JSON}")

    if script:

        tts = MultiSpeakerTTS()

        speaker_names = [speaker.name for speaker in script.speakers]

        dialogue_lines = "\n".join(
            f"{turn.speaker}: {turn.text}"
            for turn in script.dialogue
        )

        dialogue_text = f"""TTS the following conversation between {", ".join(speaker_names)}:
        {dialogue_lines}
        """

        # Dynamically assign voices
        speaker_voice_mapping = {
            speaker.name: speaker.voice_id
            for speaker in script.speakers
        }
        print(f"before validate {speaker_voice_mapping}")
        speaker_voice_mapping = build_speaker_voice_mapping(script)
        print("✅ Speaker to voice mapping:")
        for speaker, voice_id in speaker_voice_mapping.items():
            print(f"  {speaker}: {voice_id}")
        # tts.generate_tts(
        #     dialogue=dialogue_text,
        #     speaker_voice_map=speaker_voice_mapping,
        #     output_file="netcom_podcast_speaker_output.wav"
        # )

        # print(dialogue_text)
        
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
