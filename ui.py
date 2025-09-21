# ui.py
import pygame

def draw_text(screen, font, text, x, y, color=(240,240,240)):
    screen.blit(font.render(text, True, color), (x,y))

def draw_menu(screen, font, options, selected):
    screen.fill((12,16,40))
    draw_text(screen, font, "Main Menu", 40, 20, (255,230,120))
    y = 80
    for i,opt in enumerate(options):
        bg = (40,40,80) if i!=selected else (80,120,80)
        pygame.draw.rect(screen, bg, (40, y, 720, 36))
        draw_text(screen, font, opt, 60, y+8, (255,255,255))
        y += 46
    draw_text(screen, font, "Use UP/DOWN and ENTER. ESC to go back.", 40, 540, (180,180,180))

def draw_roster(screen, font, roster, selected=0):
    screen.fill((10,30,20))
    draw_text(screen, font, "Roster", 40, 20, (230,230,230))
    base_x, base_y = 40, 80
    for i, h in enumerate(roster.heroes):
        y = base_y + i*28
        if i == selected:
            pygame.draw.rect(screen, (40,80,40), (base_x-6, y-2, 700, 26))
        draw_text(screen, font, f"{i+1}. {h.name} ({h.rarity}) L{h.level} ★{h.stars} - {h.cls}", base_x, y)

def draw_battle_history(screen, font, history, selected=0):
    screen.fill((20,10,20))
    draw_text(screen, font, "Battle History (click or use arrows then ENTER to view)", 40, 20, (230,200,200))
    base_x, base_y = 40, 80
    for i, e in enumerate(reversed(history)):
        idx = len(history)-1 - i
        y = base_y + i*28
        if idx == selected:
            pygame.draw.rect(screen, (50,40,80), (base_x-6, y-2, 720, 26))
        title = e.get("title", f"Battle {idx+1}")
        outcome = "Win" if e.get("player_win") else ("Loss" if e.get("player_win") is False else "Unknown")
        draw_text(screen, font, f"{idx+1}. {title} - {outcome}", base_x, y)

def draw_battle_details(screen, font, entry):
    screen.fill((12,12,12))
    title = entry.get("title", "Battle Details")
    draw_text(screen, font, title, 40, 20, (240,240,200))
    y = 80
    rounds = entry.get("rounds", [])
    if not rounds:
        draw_text(screen, font, "No details available.", 40, y)
        return
    for r_idx, r in enumerate(rounds):
        draw_text(screen, font, f"Round {r_idx+1}:", 40, y)
        y += 24
        for line in r:
            draw_text(screen, font, line, 60, y, (220,220,220))
            y += 18
        y += 6

def draw_inventory(screen, font, inventory=None):
    screen.fill((0, 50, 0))
    draw_text(screen, font, "Inventory", 50, 50, (255,255,255))
    if inventory:
        y = 100
        for item, count in inventory.items():
            draw_text(screen, font, f"{item}: {count}", 50, y, (255,255,255))
            y += 30
    else:
        draw_text(screen, font, "Empty", 50, 100, (200,200,200))
