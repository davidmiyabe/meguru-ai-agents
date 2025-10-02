"""UI helpers for the cinematic trip planning journey."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Tuple, TypedDict

import streamlit as st

from meguru.schemas import TripIntent
from meguru.workflows.trip_pipeline import run_trip_pipeline

_WIZARD_KEY = "_plan_wizard_state"
_TRIP_INTENT_KEY = "trip_intent"
_ITINERARY_KEY = "itinerary"
_PIPELINE_ERROR_KEY = "pipeline_error"

_GROUP_TYPES = [
    "Just me",
    "Partner getaway",
    "Family crew",
    "Friends trip",
    "Workmates",
]
_PACE_OPTIONS = ["Laid back", "Balanced", "All-out"]
_BUDGET_OPTIONS = ["Shoestring", "Moderate", "Splurge"]
_VIBE_OPTIONS = [
    "Nightlife",
    "Foodie adventures",
    "Culture & history",
    "Outdoors & nature",
    "Something eclectic",
]


class _ExperienceCard(TypedDict):
    """Static representation of an experience suggestion card."""

    id: str
    title: str
    description: str
    category: str
    image_url: str
    location_hint: str


_EXPERIENCE_CARDS: List[_ExperienceCard] = [
    {
        "id": "neon_bazaar",
        "title": "Neon Night Bazaar Crawl",
        "description": "Slide into hidden bars, late-night bites, and rooftop lounges with a local host.",
        "category": "Nightlife",
        "image_url": "https://images.unsplash.com/photo-1504805572947-34fad45aed93?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Perfect for electric evenings and skyline views.",
    },
    {
        "id": "chef_counter",
        "title": "Chef's Counter Tasting Walk",
        "description": "Sample progressive bites from tucked-away kitchens and night markets.",
        "category": "Foodie adventures",
        "image_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Street markets, izakayas, and dessert bars in one swoop.",
    },
    {
        "id": "temple_stories",
        "title": "Golden Hour Temple Stories",
        "description": "A historian-led wander through quiet shrines before the crowds appear.",
        "category": "Culture & history",
        "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sunrise courtyards, incense rituals, and local legends.",
    },
    {
        "id": "coastal_cycle",
        "title": "Coastal Sunrise Cycle",
        "description": "Ride the waterfront at dawn, then refuel with a farm-to-table brunch.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1526481280695-3c46931c2ae9?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Sea breezes, hidden beaches, and artisanal coffee stops.",
    },
    {
        "id": "art_lab",
        "title": "Design District Studio Hop",
        "description": "Meet makers in their studios and craft a bespoke keepsake to take home.",
        "category": "Something eclectic",
        "image_url": "https://images.unsplash.com/photo-1529429617124-aee3713d8e2f?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Boutique ateliers, galleries, and concept stores in bloom.",
    },
    {
        "id": "forest_baths",
        "title": "Forest Bathing & Tea Ritual",
        "description": "Slow down with a guided forest walk that ends in a mindful tea ceremony.",
        "category": "Outdoors & nature",
        "image_url": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
        "location_hint": "Whispering pines, mountain views, and calming traditions.",
    },
]




def _save_custom_interest(state: Dict[str, object]) -> None:
    """Persist a custom interest from the Streamlit text input."""

    entry = st.session_state.get("plan_custom_interest_entry", "")
    cleaned = entry.strip()
    if cleaned and cleaned not in state["custom_interests"]:
        state["custom_interests"].append(cleaned)
    st.session_state["plan_custom_interest_entry"] = ""


_LOGGER = logging.getLogger(__name__)


def ensure_plan_state() -> None:
    """Initialise the Streamlit session state used by the planner UI."""

    if _WIZARD_KEY not in st.session_state:
        st.session_state[_WIZARD_KEY] = {
            "scene": "welcome",
            "destination": "",
            "date_mode": "dates",
            "start_date": None,
            "end_date": None,
            "flexible_months": [],
            "group_type": _GROUP_TYPES[1],
            "group_size": 2,
            "travel_pace": _PACE_OPTIONS[1],
            "budget": _BUDGET_OPTIONS[1],
            "vibe": [],
            "custom_interests": [],
            "notes": "",
            "liked_cards": [],
            "saved_cards": [],
            "personal_events": [],
            "share_public": True,
            "share_caption": "",
            "allow_remix": True,
            "has_generated": False,
        }

    st.session_state.setdefault(_TRIP_INTENT_KEY, None)
    st.session_state.setdefault(_ITINERARY_KEY, None)
    st.session_state.setdefault(_PIPELINE_ERROR_KEY, None)


def _wizard_state() -> Dict[str, object]:
    return st.session_state[_WIZARD_KEY]


def _month_options() -> Tuple[List[str], Dict[str, str]]:
    today = date.today().replace(day=1)
    iso_values: List[str] = []
    labels: Dict[str, str] = {}
    for offset in range(0, 12):
        month = today + timedelta(days=offset * 31)
        real_month = date(month.year, month.month, 1)
        iso = real_month.isoformat()
        if iso in iso_values:
            continue
        label = real_month.strftime("%B %Y")
        iso_values.append(iso)
        labels[iso] = label
    return iso_values, labels


def _render_cinematic_intro(container, state: Dict[str, object]) -> None:
    container.markdown(
        """
        <div style="background: linear-gradient(120deg, #040b1a, #1c2b4d); padding: 3rem 2.4rem; border-radius: 24px;">
          <p style="color: rgba(255,255,255,0.75); letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.2rem;">Scene One</p>
          <h2 style="color: white; font-size: 2.8rem; margin: 0;">Where do you want to go?</h2>
          <p style="color: rgba(255,255,255,0.85); max-width: 640px; font-size: 1.05rem;">
            Picture sweeping drone shots and cinematic music. Drop the destination and we'll craft the opening act of your journey.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    destination = container.text_input(
        "Destination",
        value=str(state.get("destination", "")),
        key="plan_destination_input",
        placeholder="Kyoto, Lisbon, Reykjavik…",
    )
    state["destination"] = destination.strip()

    cta = container.button(
        "Start the adventure",
        type="primary",
        use_container_width=True,
        key="plan_start_cta",
    )
    if cta:
        if state["destination"]:
            state["scene"] = "conversation"
            st.session_state[_PIPELINE_ERROR_KEY] = None
        else:
            container.warning("Tell us where you're headed to roll the trailer.")

    container.caption("You can always come back to change the destination later.")


def _render_conversation(container, state: Dict[str, object]) -> None:
    container.markdown(
        f"""
        ### Let's talk about your {state.get('destination', 'trip')} 🎬
        We'll keep things conversational—answer like you're chatting with a travel-savvy friend.
        """
    )

    with container.form("plan_conversation_form", clear_on_submit=False):
        group_index = (
            _GROUP_TYPES.index(state["group_type"])
            if state.get("group_type") in _GROUP_TYPES
            else 0
        )
        group_type = st.selectbox(
            "Who’s coming along on this adventure?",
            options=_GROUP_TYPES,
            index=group_index,
        )
        group_size = st.slider(
            "How big is the crew?",
            min_value=1,
            max_value=12,
            value=int(state.get("group_size", 2)),
        )

        date_mode = st.radio(
            "Are you thinking of traveling in a specific month, or are your dates flexible?",
            options=("Specific dates", "I'm flexible"),
            index=0 if state.get("date_mode") == "dates" else 1,
        )

        start_date = state.get("start_date")
        end_date = state.get("end_date")
        flexible_months: List[str] = list(state.get("flexible_months", []))

        if date_mode == "Specific dates":
            today = date.today()
            default_start = start_date or today + timedelta(days=30)
            default_end = end_date or default_start + timedelta(days=4)
            selected_dates = st.date_input(
                "Lock in your travel window",
                value=(default_start, default_end),
                min_value=today,
            )
            if isinstance(selected_dates, tuple):
                start_date, end_date = selected_dates
            else:
                start_date = end_date = selected_dates
            flexible_months = []
        else:
            iso_values, labels = _month_options()
            default_labels = [
                labels[value] for value in flexible_months if value in labels
            ]
            selected_labels = st.multiselect(
                "Pick a few months that would work",
                options=[labels[value] for value in iso_values],
                default=default_labels,
            )
            reverse_lookup = {label: iso for iso, label in labels.items()}
            flexible_months = [reverse_lookup[label] for label in selected_labels]
            start_date = None
            end_date = None

        vibe_selection = st.multiselect(
            "What kind of vibe are you craving?",
            options=_VIBE_OPTIONS,
            default=list(state.get("vibe", [])),
            help="Select as many as you like—this helps us pick experiences you’ll love.",
        )

        travel_pace_index = (
            _PACE_OPTIONS.index(state.get("travel_pace", _PACE_OPTIONS[1]))
            if state.get("travel_pace") in _PACE_OPTIONS
            else 1
        )
        travel_pace = st.select_slider(
            "How packed should the days feel?",
            options=_PACE_OPTIONS,
            value=_PACE_OPTIONS[travel_pace_index],
        )

        budget_index = (
            _BUDGET_OPTIONS.index(state.get("budget", _BUDGET_OPTIONS[1]))
            if state.get("budget") in _BUDGET_OPTIONS
            else 1
        )
        budget = st.selectbox(
            "Any budget vibes we should respect?",
            options=_BUDGET_OPTIONS,
            index=budget_index,
        )

        notes = st.text_area(
            "Anything else we should know?",
            value=str(state.get("notes", "")),
            placeholder="Wishlist items, must-eats, or deal-breakers…",
        )

        submitted = st.form_submit_button(
            "Next: Explore inspiration",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            errors: List[str] = []
            if not state.get("destination"):
                errors.append("Drop a destination on the previous screen.")
            if date_mode == "Specific dates" and (start_date is None or end_date is None):
                errors.append("Choose start and end dates or switch to flexible months.")
            if not vibe_selection:
                errors.append("Pick at least one vibe so we know what to surface.")

            if errors:
                for message in errors:
                    st.warning(message)
            else:
                state.update(
                    {
                        "group_type": group_type,
                        "group_size": group_size,
                        "date_mode": "dates" if date_mode == "Specific dates" else "months",
                        "start_date": start_date,
                        "end_date": end_date,
                        "flexible_months": flexible_months,
                        "vibe": list(vibe_selection),
                        "travel_pace": travel_pace,
                        "budget": budget,
                        "notes": notes.strip(),
                    }
                )
                st.session_state[_PIPELINE_ERROR_KEY] = None
                state["scene"] = "interests"

    if container.button("Back to cinematic intro", key="plan_back_intro"):
        state["scene"] = "welcome"


def _render_interest_gallery(container, state: Dict[str, object]) -> None:
    destination = state.get("destination") or "your trip"
    container.markdown(
        f"""
        ### Curate the vibe for {destination}
        Tap ❤️ to teach Meguru what you love and 🔖 to save it straight into your moodboard.
        """
    )

    if container.button("Back to questions", key="plan_back_conversation"):
        state["scene"] = "conversation"
        return

    vibe_tags = sorted(set(state.get("vibe", [])))
    if vibe_tags:
        chips = " ".join(f"`{tag}`" for tag in vibe_tags)
        container.caption(f"Dialling in on: {chips}")

    error_message = st.session_state.get(_PIPELINE_ERROR_KEY)
    if error_message:
        container.error(error_message)

    columns = container.columns(3, gap="large")
    for idx, card in enumerate(_EXPERIENCE_CARDS):
        target = columns[idx % len(columns)]
        with target:
            st.image(card["image_url"], use_column_width=True)
            st.markdown(f"**{card['title']}**")
            st.caption(card["description"])
            st.caption(f"_{card['location_hint']}_")
            like_key = f"plan_like_{card['id']}"
            save_key = f"plan_save_{card['id']}"
            liked = st.toggle("❤️ Like", key=like_key, value=card["id"] in state["liked_cards"])
            saved = st.toggle("🔖 Save", key=save_key, value=card["id"] in state["saved_cards"])
            if liked and card["id"] not in state["liked_cards"]:
                state["liked_cards"].append(card["id"])
            elif not liked and card["id"] in state["liked_cards"]:
                state["liked_cards"].remove(card["id"])

            if saved and card["id"] not in state["saved_cards"]:
                state["saved_cards"].append(card["id"])
            elif not saved and card["id"] in state["saved_cards"]:
                state["saved_cards"].remove(card["id"])

    container.text_input(
        "Add your own must-do (press enter to keep it)",
        key="plan_custom_interest_entry",
        placeholder="Vinyl record shops, rooftop yoga, tiny bookstores…",
    )
    container.button(
        "Save custom interest",
        key="plan_add_custom_interest",
        on_click=_save_custom_interest,
        kwargs={"state": state},
    )

    if state["custom_interests"]:
        container.write(
            "Custom interests: "
            + ", ".join(f"`{interest}`" for interest in state["custom_interests"])
        )

    generate_clicked = container.button(
        "Generate my itinerary",
        type="primary",
        use_container_width=True,
        key="plan_generate_itinerary",
    )
    if generate_clicked:
        success = _handle_submit(state)
        if success:
            return

    container.caption(
        "Want to tweak something? Head back to the questions or keep liking cards for a different mix."
    )


def _render_review(container, state: Dict[str, object]) -> None:
    container.markdown("### Your itinerary is live ✨")

    itinerary = st.session_state.get(_ITINERARY_KEY)
    intent: TripIntent | None = st.session_state.get(_TRIP_INTENT_KEY)

    if not itinerary or not intent:
        container.info(
            "Generate an itinerary to unlock sharing and remix features."
        )
        if container.button("Back to inspiration gallery", key="plan_review_back"):
            state["scene"] = "interests"
        return

    container.success(
        "Itinerary ready! Jump over to the **Itinerary** tab for the full cinematic breakdown."
    )

    bullets: List[str] = []
    if intent.start_date and intent.end_date:
        bullets.append(
            f"Dates: {intent.start_date.strftime('%b %d, %Y')} – {intent.end_date.strftime('%b %d, %Y')}"
        )
    elif state.get("flexible_months"):
        month_labels = [
            date.fromisoformat(month).strftime("%B %Y")
            for month in state["flexible_months"]
        ]
        bullets.append("Timing: flexible across " + ", ".join(month_labels))

    bullets.append(
        f"Crew: {state.get('group_type', 'Travelers')} (x{int(state.get('group_size', 1))})"
    )
    if intent.travel_pace:
        bullets.append(f"Pace: {intent.travel_pace}")
    if intent.budget:
        bullets.append(f"Budget: {intent.budget}")

    if bullets:
        container.markdown("- " + "\n- ".join(bullets))

    if state.get("personal_events"):
        container.markdown(
            "**Your personal additions**\n" + "\n".join(f"• {item}" for item in state["personal_events"])
        )

    container.markdown("#### Make it yours")
    custom_event = container.text_input(
        "Drop in your own moment",
        key="plan_custom_event_entry",
        placeholder="Sunset picnic at Arashiyama bamboo grove",
    )
    if container.button("Add to my itinerary", key="plan_add_custom_event"):
        cleaned = custom_event.strip()
        if cleaned and cleaned not in state["personal_events"]:
            state["personal_events"].append(cleaned)
        st.session_state["plan_custom_event_entry"] = ""

    container.markdown("#### Share the inspiration")
    share_public = container.toggle(
        "Share to the Meguru community feed",
        key="plan_share_public",
        value=bool(state.get("share_public", True)),
    )
    allow_remix = container.toggle(
        "Let other travellers remix this itinerary",
        key="plan_allow_remix",
        value=bool(state.get("allow_remix", True)),
    )
    share_caption = container.text_area(
        "Add a caption for your profile",
        value=str(state.get("share_caption", "")),
        key="plan_share_caption",
        placeholder="Tell the community why this trip is iconic…",
    )

    state.update(
        {
            "share_public": share_public,
            "allow_remix": allow_remix,
            "share_caption": share_caption.strip(),
        }
    )

    action_cols = container.columns([1, 1, 1])
    if action_cols[0].button("Explore more ideas", key="plan_review_more"):
        state["scene"] = "interests"
    if action_cols[1].button("Regenerate itinerary", key="plan_review_regen"):
        _handle_submit(state)
    if action_cols[2].button("Copy share link", key="plan_review_share"):
        container.info("Link copied! (Imagine social magic happening here.)")


def _build_trip_intent(state: Dict[str, object]) -> TripIntent:
    destination = str(state.get("destination", "")).strip()
    if not destination:
        raise ValueError("Destination is required")

    start_date = state.get("start_date")
    end_date = state.get("end_date")
    duration_days = None
    if isinstance(start_date, date) and isinstance(end_date, date) and end_date >= start_date:
        duration_days = (end_date - start_date).days + 1

    interests_set = set(state.get("vibe", [])) | set(state.get("custom_interests", []))
    liked_cards = set(state.get("liked_cards", []))
    saved_cards = set(state.get("saved_cards", []))
    for card in _EXPERIENCE_CARDS:
        if card["id"] in liked_cards or card["id"] in saved_cards:
            interests_set.add(card["category"])
            if card["id"] in saved_cards:
                interests_set.add(card["title"])

    notes_segments: List[str] = []
    if state.get("flexible_months"):
        months = ", ".join(
            date.fromisoformat(month).strftime("%B %Y")
            for month in state["flexible_months"]
        )
        notes_segments.append(f"Flexible timing: {months}")

    group_type = state.get("group_type")
    group_size = state.get("group_size")
    if group_type:
        notes_segments.append(f"Group: {group_type} ({int(group_size or 1)} travellers)")

    if state.get("personal_events"):
        notes_segments.append(
            "Personal additions: " + "; ".join(state["personal_events"])
        )

    existing_notes = str(state.get("notes", "")).strip()
    if existing_notes:
        notes_segments.append(existing_notes)

    combined_notes = "\n".join(notes_segments) if notes_segments else None

    return TripIntent(
        destination=destination,
        start_date=start_date if isinstance(start_date, date) else None,
        end_date=end_date if isinstance(end_date, date) else None,
        duration_days=duration_days,
        travel_pace=str(state.get("travel_pace")) if state.get("travel_pace") else None,
        budget=str(state.get("budget")) if state.get("budget") else None,
        interests=sorted(interests_set),
        notes=combined_notes,
    )


def _format_pipeline_error(exc: Exception) -> str:
    base_message = "Unable to generate the itinerary."
    details = str(exc).strip()
    if details:
        lowered = details.lower()
        if "google_maps_api_key" in lowered:
            return (
                f"{base_message} Add a Google Maps API key by setting the "
                "GOOGLE_MAPS_API_KEY environment variable."
            )
        if "openai" in lowered and any(token in lowered for token in ("api key", "401", "unauthorized")):
            return (
                f"{base_message} Provide an OpenAI API key via the "
                "OPENAI_API_KEY environment variable."
            )
        if "429" in lowered or "too many requests" in lowered:
            return (
                f"{base_message} The OpenAI API rate limit was hit. Wait a moment and try again."
            )
        return f"{base_message} {details}"
    return f"{base_message} Check your configuration and try again."


def _handle_submit(state: Dict[str, object]) -> bool:
    if not state.get("destination"):
        st.warning("Add a destination first.")
        return False

    try:
        intent = _build_trip_intent(state)
    except ValueError as exc:
        st.warning(str(exc))
        return False

    itinerary_placeholder = st.session_state.get(_ITINERARY_KEY)
    st.session_state[_TRIP_INTENT_KEY] = intent

    try:
        with st.spinner("Generating your itinerary…"):
            itinerary = run_trip_pipeline(intent)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user
        friendly_message = _format_pipeline_error(exc)
        _LOGGER.exception("Trip pipeline failed")
        st.session_state[_PIPELINE_ERROR_KEY] = friendly_message
        st.session_state[_ITINERARY_KEY] = itinerary_placeholder
        st.error(friendly_message)
        return False

    st.session_state[_PIPELINE_ERROR_KEY] = None
    st.session_state[_ITINERARY_KEY] = itinerary
    st.session_state["_focus_itinerary"] = True
    state["scene"] = "review"
    state["has_generated"] = True
    st.success("Itinerary ready! Check the Itinerary tab for details.")
    return True


def render_plan_tab(container) -> None:
    """Render the plan wizard inside the provided container."""

    state = _wizard_state()

    with container:
        scene = state.get("scene", "welcome")
        if scene == "welcome":
            _render_cinematic_intro(st, state)
        elif scene == "conversation":
            _render_conversation(st, state)
        elif scene == "interests":
            _render_interest_gallery(st, state)
        else:
            _render_review(st, state)
