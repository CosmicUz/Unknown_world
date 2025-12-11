import pygame
from menu import Menu


def show_start_screen(width=1200, height=800):
    pygame.init()
    fullscreen = False
    run_screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 72)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        run_screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        run_screen = pygame.display.set_mode((width, height))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                center_x, center_y = run_screen.get_width() // 2, run_screen.get_height() // 2
                radius = 120
                if (mx - center_x) ** 2 + (my - center_y) ** 2 <= radius ** 2:
                    running = False
        run_screen.fill((45, 180, 22))
        center_x, center_y = run_screen.get_width() // 2, run_screen.get_height() // 2
        pygame.draw.circle(run_screen, (70, 160, 230), (center_x, center_y), 120)
        pygame.draw.circle(run_screen, (255, 255, 255), (center_x, center_y), 120, 6)
        text = font.render("START", True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        run_screen.blit(text, text_rect)
        pygame.display.flip()
        clock.tick(60)
    return run_screen, run_screen.get_width(), run_screen.get_height(), fullscreen


if __name__ == "__main__":
    run_screen, width, height, fullscreen = show_start_screen()
    menu = Menu(screen=run_screen, screen_width=width, screen_height=height)
    menu.run()