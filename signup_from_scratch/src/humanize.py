"""Human-like interaction helpers for nodriver.

Goal: avoid the robotic tells CF/Turnstile flag — instant field fills,
zero mouse movement, sub-millisecond form completion. These add jitter,
reading pauses, and real cursor movement before clicks.
"""

import asyncio
import random

import nodriver as uc


async def pause(lo: float = 0.4, hi: float = 1.2) -> None:
    """Random short pause (thinking/reading)."""
    await asyncio.sleep(random.uniform(lo, hi))


async def read_pause() -> None:
    """Longer pause, as if reading the page."""
    await asyncio.sleep(random.uniform(1.5, 3.5))


async def move_to(page: uc.Tab, element, jitter: bool = True) -> None:
    """Move the cursor onto an element before interacting (Turnstile watches this)."""
    try:
        await element.scroll_into_view()
        await pause(0.2, 0.6)
        await element.mouse_move()
        if jitter:
            # a couple of small drift moves near the target
            pos = await element.get_position()
            if pos:
                cx = pos.center[0] if hasattr(pos, "center") else (pos.x + pos.width / 2)
                cy = pos.center[1] if hasattr(pos, "center") else (pos.y + pos.height / 2)
                for _ in range(random.randint(1, 3)):
                    await page.mouse_move(
                        cx + random.uniform(-8, 8),
                        cy + random.uniform(-6, 6),
                        steps=random.randint(4, 9),
                    )
                    await asyncio.sleep(random.uniform(0.05, 0.2))
    except Exception:
        # movement is best-effort; never fail the flow over cursor jitter
        pass


async def human_click(page: uc.Tab, element) -> None:
    """Move to element, then click with a small pre-click pause."""
    await move_to(page, element)
    await pause(0.15, 0.5)
    await element.click()


async def human_type(element, text: str) -> None:
    """Type char-by-char with variable delays and occasional longer pauses."""
    for ch in text:
        await element.send_keys(ch)
        delay = random.uniform(0.06, 0.22)
        if random.random() < 0.08:
            delay += random.uniform(0.3, 0.9)  # occasional hesitation
        await asyncio.sleep(delay)


async def human_scroll(page: uc.Tab) -> None:
    """A little natural scrolling."""
    try:
        for _ in range(random.randint(1, 3)):
            await page.scroll_down(random.randint(80, 220))
            await asyncio.sleep(random.uniform(0.3, 0.8))
    except Exception:
        pass
