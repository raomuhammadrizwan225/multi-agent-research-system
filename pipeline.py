from agents import (
    critic_chain,
    generate_report,
    run_reader_agent,
    run_search_agent,
)


def run_research_pipeline(topic: str) -> dict:
    state = {}

    print("\nStep 1 - Search Agent")
    state["search_results"] = run_search_agent(topic)
    print("\nSearch Agent URLs:\n", state["search_results"])

    print("\nStep 2 - Reader Agent")
    state["reader_results"] = run_reader_agent(
        topic,
        state["search_results"],
    )
    print("\nReader Agent Output:\n", state["reader_results"])

    print("\nStep 3 - Writer")
    research_material = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"READER SUMMARIES:\n{state['reader_results']}"
    )
    state["report"] = generate_report(topic, research_material)
    print("\nFinal Report:\n", state["report"])

    print("\nStep 4 - Critic")
    state["feedback"] = critic_chain.invoke(
        {"report": state["report"]}
    )
    print("\nCritic Feedback:\n", state["feedback"])

    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ").strip()

    if not topic:
        raise SystemExit("A research topic is required.")

    run_research_pipeline(topic)
