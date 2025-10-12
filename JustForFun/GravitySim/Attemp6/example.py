import re
import pygame
import sys
import math
import os
import sys
import random

import collections



WIDTH, HEIGHT = 1280, 649

gravity_multiplier = 1.0
G = 6.67430e0
FPS = 300

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
scrapedSounds = {}

musicBackgroundListPath = [
    resource_path("assets/BackgroundMusics/space1.mp3"),
    resource_path("assets/BackgroundMusics/space2.mp3"),
    resource_path("assets/BackgroundMusics/space3.mp3"),
    resource_path("assets/BackgroundMusics/space4.mp3"),
    resource_path("assets/BackgroundMusics/space5.mp3"),
    resource_path("assets/BackgroundMusics/space6.mp3"),
    resource_path("assets/BackgroundMusics/space7.mp3"),
    resource_path("assets/BackgroundMusics/space8.mp3"),
    resource_path("assets/BackgroundMusics/space9.mp3"),
]

musicExplodeListPath = [
    resource_path("assets/ExplosionSoundEffects/Explode1.mp3"),
    resource_path("assets/ExplosionSoundEffects/Explode2.mp3"),
    resource_path("assets/ExplosionSoundEffects/Explode3.mp3"),
    resource_path("assets/ExplosionSoundEffects/Explode4.mp3"),
    resource_path("assets/ExplosionSoundEffects/Explode5.mp3"),
]

pygame.mixer.init()
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Astrophysics Simulator")
clock = pygame.time.Clock()

def draw_button(screen, x, y, w, h, text, active=False):
    color = (100, 200, 255) if active else (60, 60, 90)
    pygame.draw.rect(screen, color, (x, y, w, h), border_radius=8)
    font = pygame.font.Font(None, 28)
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (x + w//2 - label.get_width()//2, y + h//2 - label.get_height()//2))
    return pygame.Rect(x, y, w, h)

class Body:
    def __init__(self, x, y, mass, radius, color, body_type="planet"):
        self.x = x
        self.y = y
        self.mass = mass
        self.radius = radius
        self.color = color
        self.body_type = body_type
        self.vx = 0
        self.vy = 0
        self.trail = []
        self.max_trail_length = 200
        self.consumption_radius = radius * 2
        self.original_mass = mass
        self.pulse_phase = 0
        self.mass_history = collections.deque(maxlen=300)
        self.age = 0
        self.selected = False
        self.last_force = (0, 0)
        self.ejection_timer = 0

    def evaporate(self):
        """Black hole slowly loses mass (Hawking radiation)"""
        if self.body_type == "black_hole":
            self.mass -= max(0.01, self.mass * 0.0002)
            if self.mass < 650:
                return True
        return False

    def can_consume(self, other):
        """Check if this body can consume another body or particle"""
        if self.body_type in ["planet", "star", "neutron_star", "black_hole"]:
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            return dist < self.consumption_radius
        return False

    def consume(self, other):
        """Consume another body or particle"""
        if hasattr(other, 'mass'):  # It's a body
            self.mass += other.mass * 0.8  # 80% mass transfer efficiency
        else:  # It's a particle
            self.mass += other.mass
        
        # Update radius based on new mass
        if self.body_type == "star":
            self.radius = max(8, int(self.mass ** 0.4))
            self.consumption_radius = self.radius * 2
        elif self.body_type == "neutron_star":
            self.radius = max(6, min(12, int(self.mass ** 0.2)))  # Neutron stars are dense
            self.consumption_radius = self.radius * 2.5
        elif self.body_type == "black_hole":
            self.radius = max(10, int(self.mass ** 0.3))
            self.consumption_radius = self.radius * 3  # Black holes have strong pull

    def should_collapse(self):
        """Check if planet should become a star, or if star is too small and should explode, or if star/neutron star should collapse"""
        if self.body_type == "planet" and self.mass > 150:
            return "planet_to_star"
        if self.body_type == "star":
            if self.mass > 350:
                return "star_to_neutron"
            elif self.mass < 50:
                return "star_to_particles"
        elif self.body_type == "neutron_star":
            if self.mass > 800:
                print(str(self.body_type).__add__(" : ".__add__(str(self.mass))))
                return "neutron_to_bh"
            elif self.mass < 350:
                return "neutron_to_particles"
        if self.body_type == "black_hole":
            if self.mass > 100000:
                return "trigger_supernova"
        return None

    def collapse_to_star(self):
        """Transform planet into star"""
        self.body_type = "star"
        self.radius = max(8, int(self.mass ** 0.4))
        self.color = (255, 255, 100)
        self.consumption_radius = self.radius * 2
        return []

    def collapse_to_neutron_star(self):
        """Transform star into neutron star"""
        self.body_type = "neutron_star"
        self.mass *= 0.7  # Some mass is lost in collapse
        self.radius = max(6, min(12, int(self.mass ** 0.2)))
        self.color = (200, 200, 255)  # Blueish white
        self.consumption_radius = self.radius * 2.5
        return []  # No particles released for neutron star formation

    def explode_to_particles_and_planets(self):
        """Explode into particles and/or small planets, conserving mass"""
        particles = []
        planets = []
        total_mass = self.mass
        num_planets = random.randint(1, 3)
        planet_masses = [random.uniform(5, 15) for _ in range(num_planets)]
        planet_mass_sum = sum(planet_masses)
        # Scale so total planet mass is at most 60% of total
        scale = (total_mass * 0.6) / planet_mass_sum if planet_mass_sum > 0 else 0
        planet_masses = [m * scale for m in planet_masses]
        # Remaining mass goes to particles
        particle_mass = total_mass - sum(planet_masses)
        num_particles = max(10, int(particle_mass // 2))


        remaining_mass = total_mass - sum(planet_masses)
        particle_mass = remaining_mass / num_particles
        # Add safety clamp
        particle_mass = max(0.01, particle_mass)

        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 6)
            vx = self.vx + math.cos(angle) * speed
            vy = self.vy + math.sin(angle) * speed
            color = (255, 200, 100)
            particles.append(Particle(self.x, self.y, vx, vy, color, mass=particle_mass/num_particles))
        for pm in planet_masses:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(20, 40)
            px = self.x + math.cos(angle) * dist
            py = self.y + math.sin(angle) * dist
            vx = self.vx + math.cos(angle) * 2
            vy = self.vy + math.sin(angle) * 2
            color = random_color()
            radius = max(3, int(pm))
            planets.append(Body(px, py, pm, radius, color, "planet"))
        return particles, planets

    def newtonian_force(self, other):
        """Calculate Newtonian gravitational force between two bodies"""
        dx = other.x - self.x
        dy = other.y - self.y
        dist_sq = dx**2 + dy**2
        dist = math.sqrt(dist_sq)
        
        if dist < self.radius + other.radius:
            return 0, 0
            
        force = gravity_multiplier * G * self.mass * other.mass / (dist_sq + 1e-2)
        
        # Black holes have stronger gravitational pull
        if self.body_type == "black_hole":
            force *= 2
        elif other.body_type == "black_hole":
            force *= 2
            
        theta = math.atan2(dy, dx)
        fx = math.cos(theta) * force
        fy = math.sin(theta) * force
        return fx, fy

    def gr_force(self, other):
        """Calculate force with general relativity correction"""
        dx = other.x - self.x
        dy = other.y - self.y
        dist_sq = dx**2 + dy**2
        dist = math.sqrt(dist_sq)
        
        if dist < self.radius + other.radius:
            return 0, 0
            
        # Standard Newtonian force
        force = gravity_multiplier * G * self.mass * other.mass / (dist_sq + 1e-2)
        
        # Add relativistic correction: (1 + 3*rs/r)
        rs = 2 * G * other.mass / (3e8**2)  # Schwarzschild radius
        correction = 1 + 3 * rs / (dist + 1e-2)
        force *= correction
        
        # Black holes have even stronger relativistic effects
        if self.body_type == "black_hole" or other.body_type == "black_hole":
            force *= 1.5
        
        theta = math.atan2(dy, dx)
        fx = math.cos(theta) * force
        fy = math.sin(theta) * force
        return fx, fy

    def update(self, bodies, particle_system, theory="Newtonian", time_scale=1.0):
        """Update body position and velocity with screen wrapping and mass loss for stars/neutron stars"""
        fx, fy = 0, 0        
        for other in bodies:
            if other is self:
                continue
            if theory == "Newtonian":
                dfx, dfy = self.newtonian_force(other)
            else:
                dfx, dfy = self.gr_force(other)
            fx += dfx
            fy += dfy
        self.last_force = (fx, fy)
        # Update velocity and position
        self.vx += (fx / self.mass / FPS) * time_scale
        self.vy += (fy / self.mass / FPS) * time_scale
        self.x += self.vx * time_scale
        self.y += self.vy * time_scale
        
        mass_loss = 0
        if self.body_type == "star":
            mass_loss = max(0.01, self.mass * 0.0001)
        elif self.body_type == "neutron_star":
            mass_loss = max(0.005, self.mass * 0.00005)
        self.ejection_timer += 1 * time_scale
        if self.ejection_timer >= 30:  # every 6 frames
            if mass_loss > 0 and self.mass > mass_loss:
                self.mass -= mass_loss
                eject_particles(self.x, self.y, self.vx, self.vy, mass_loss, particle_system, self.body_type)
                self.ejection_timer = 0

        # Wrap around screen edges, but not into the UI bar
        if self.x < -self.radius:
            self.trail.clear()
            self.x = WIDTH + self.radius
        elif self.x > WIDTH + self.radius:
            self.trail.clear()
            self.x = -self.radius

        # Only wrap vertically within the simulation area (not into the UI bar)
        sim_height = HEIGHT - 200  # 200 is your UI_BAR_HEIGHT
        if self.y < -self.radius:
            self.trail.clear()
            self.y = sim_height + self.radius
        elif self.y > sim_height + self.radius:
            self.trail.clear()
            self.y = -self.radius
        
        # Update pulse phase for visual effects
        self.pulse_phase += 0.1 * time_scale
        
        # Update trail
        self.trail.append((int(self.x), int(self.y)))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)
        self.age += 0.05 * time_scale
        self.mass_history.append((self.age, self.mass))

    def draw(self, screen, show_trail=True):
        """Draw the body and its trail with special effects"""
        # Draw trail with fading effect
        if show_trail and len(self.trail) > 2:
            for i in range(1, len(self.trail)):
                alpha = i / len(self.trail)
                trail_color = tuple(int(c * alpha) for c in self.color)
                if i < len(self.trail) - 1:
                    pygame.draw.line(screen, trail_color, self.trail[i-1], self.trail[i], 2)
        
        # Draw consumption radius for stars, neutron stars, and black holes
        if self.body_type in ["star", "neutron_star", "black_hole"]:
            consumption_color = (*self.color, 30)
            consumption_surf = pygame.Surface((self.consumption_radius * 2, self.consumption_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(consumption_surf, consumption_color, 
                             (self.consumption_radius, self.consumption_radius), self.consumption_radius)
            screen.blit(consumption_surf, (int(self.x - self.consumption_radius), int(self.y - self.consumption_radius)))
        
        # Special effects for different body types
        if self.body_type == "star":
            # Pulsing glow effect
            glow_radius = self.radius + 5 + int(3 * math.sin(self.pulse_phase))
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_color = (*self.color, 50)
            pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surf, (int(self.x - glow_radius), int(self.y - glow_radius)))
            
        elif self.body_type == "neutron_star":
            # Rapid pulsing effect
            pulse_radius = self.radius + 3 + int(2 * math.sin(self.pulse_phase * 3))
            pulse_surf = pygame.Surface((pulse_radius * 2, pulse_radius * 2), pygame.SRCALPHA)
            pulse_color = (200, 200, 255, 80)
            pygame.draw.circle(pulse_surf, pulse_color, (pulse_radius, pulse_radius), pulse_radius)
            screen.blit(pulse_surf, (int(self.x - pulse_radius), int(self.y - pulse_radius)))
            

        elif self.body_type == "black_hole":
            # Accretion disk effect grows with mass
            disk_radius = int(self.radius * 2.5)
            for i in range(3):
                alpha = 40
                disk_color = (
                    min(255, 80 + int(self.mass)), 
                    0, 
                    min(255, 80 + int(self.mass)), 
                    alpha
                )
                disk_surf = pygame.Surface((disk_radius * 2, disk_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(disk_surf, disk_color, (disk_radius, disk_radius), disk_radius - i * 2)
                screen.blit(disk_surf, (int(self.x - disk_radius), int(self.y - disk_radius)))
        
        # Draw main body
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

    def explode_to_supernova(self):
        """Explode into supernova particles"""
        particles = []
        num_particles = min(100, int(self.mass // 3))
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 8)
            vx = self.vx + math.cos(angle) * speed
            vy = self.vy + math.sin(angle) * speed
            color = (255, random.randint(100, 200), random.randint(0, 100))  # Reddish explosion
            particles.append(Particle(self.x, self.y, vx, vy, color))
        return particles

class Particle:
    def __init__(self, x, y, vx, vy, color, mass=2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.mass = mass  # Add mass to each particle
        self.age = 0
        self.mass_history = collections.deque(maxlen=300)
        self.selected = False

    def update(self, time_scale = 1.0):
        """Update particle position with screen wrapping"""
        self.x += self.vx * time_scale
        self.y += self.vy * time_scale
        self.age += 1 * time_scale
        self.mass_history.append((self.age, self.mass))
    
        # Wrap around screen edges
        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0
    
        sim_height = HEIGHT - 200  # 200 is your UI_BAR_HEIGHT
        if self.y < 0:
            self.y = sim_height
        elif self.y > sim_height:
            self.y = 0

    def draw(self, screen):
        """Draw particle"""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), max(2, int(self.mass ** 0.5)))

# Update ParticleSystem's add_explosion to distribute mass
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_explosion(self, body, num_particles=30):
        """Add explosion particles from a body, distributing mass"""
        particle_mass = body.mass / num_particles
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 4)
            vx = body.vx + math.cos(angle) * speed
            vy = body.vy + math.sin(angle) * speed
            color = body.color
            self.particles.append(Particle(body.x, body.y, vx, vy, color, mass=particle_mass))

    def update(self, bodies=None, time_scale=1.0):
        """Update all particles and allow them to be attracted by bodies and other particles"""
        particles_to_remove = []
        for idx, particle in enumerate(self.particles):
            fx, fy = 0, 0
            # Attract by all bodies
            if bodies:
                for body in bodies:
                    dx = body.x - particle.x
                    dy = body.y - particle.y
                    dist_sq = dx**2 + dy**2
                    if dist_sq < 1e-2:
                        continue
                    force = G * particle.mass * body.mass / (dist_sq + 1e-2)
                    theta = math.atan2(dy, dx)
                    fx += math.cos(theta) * force
                    fy += math.sin(theta) * force
            for other in self.particles:
                if other is particle:
                    continue
                dx = other.x - particle.x
                dy = other.y - particle.y
                dist_sq = dx**2 + dy**2
                if dist_sq < 1e-2:
                    continue
                force = G * particle.mass * other.mass / (dist_sq + 1e-2)
                theta = math.atan2(dy, dx)
                fx += math.cos(theta) * force
                fy += math.sin(theta) * force
            # Avoid division by zero for mass
            if abs(particle.mass) < 1e-8:
                particles_to_remove.append(idx)
                continue
            particle.vx += (fx / particle.mass / FPS) * time_scale
            particle.vy += (fy / particle.mass / FPS) * time_scale
            particle.update(time_scale)
        # Remove zero-mass particles
        for idx in reversed(particles_to_remove):
            self.particles.pop(idx)

    def try_combine_particles(self, bodies):
        """Try to combine particles into a new body when 5 or more are close together"""
        if len(self.particles) < 5:
            return

        eligible_particles = [p for p in self.particles if p.age > 30]
        if len(eligible_particles) < 5:
            return

        for i, center in enumerate(eligible_particles):
            close_particles = []
            for j, particle in enumerate(eligible_particles):
                if math.hypot(particle.x - center.x, particle.y - center.y) < 30:
                    close_particles.append(particle)

            if len(close_particles) >= 5:
                new_body = self._combine_particles(close_particles)
                if new_body:
                    bodies.append(new_body)
                    for particle in close_particles:
                        if particle in self.particles:
                            self.particles.remove(particle)
                break  # Only combine one cluster per frame

    def _combine_particles(self, particles):
        """Combine particles into a new body"""
        avg_x = sum(p.x for p in particles) / len(particles)
        avg_y = sum(p.y for p in particles) / len(particles)
        avg_vx = sum(p.vx for p in particles) / len(particles)
        avg_vy = sum(p.vy for p in particles) / len(particles)
        total_mass = sum(p.mass for p in particles)
        color = random_color()
        radius = max(3, int(total_mass * 0.8) // 2)
        new_body = Body(avg_x, avg_y, total_mass, radius, color)
        new_body.vx = avg_vx
        new_body.vy = avg_vy
        return new_body
    
    def draw(self, screen):
        """Draw all particles"""
        for particle in self.particles:
            particle.draw(screen)

# In your main loop, update particles with bodies:
# particle_system.update(bodies)

def random_color():
    """Generate a random bright color"""
    return (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))

def draw_slider(screen, x, y, w, h, min_val, max_val, value, label, color=(200, 200, 255)):
    """Draw a slider UI element"""
    # Clamp value to range
    value = max(min_val, min(max_val, value))
    
    # Draw bar background
    pygame.draw.rect(screen, (40, 40, 60), (x, y, w, h), border_radius=6)
    
    # Draw bar fill
    fill_ratio = (value - min_val) / (max_val - min_val)
    fill_w = int(fill_ratio * w)
    pygame.draw.rect(screen, color, (x, y, fill_w, h), border_radius=6)
    
    # Draw knob
    knob_x = x + fill_w
    pygame.draw.circle(screen, (255, 255, 255), (knob_x, y + h//2), h//2)
    
    # Draw label and value
    font = pygame.font.Font(None, 24)
    label_surf = font.render(f"{label}: {value:.1f}", True, (255, 255, 255))
    screen.blit(label_surf, (x, y - 28))
    
    return pygame.Rect(x, y, w, h), pygame.Rect(knob_x - h//2, y, h, h)

def draw_dropdown(screen, x, y, w, h, options, selected_idx, open_dropdown):
    """Draw a dropdown UI element"""
    font = pygame.font.Font(None, 28)
    
    # Draw main box
    pygame.draw.rect(screen, (60, 60, 90), (x, y, w, h), border_radius=6)
    label = font.render(options[selected_idx], True, (255, 255, 255))
    screen.blit(label, (x + 10, y + h//4))
    
    # Draw arrow
    arrow_points = [(x + w - 25, y + h//3), (x + w - 10, y + h//3), (x + w - 17, y + 2*h//3)]
    pygame.draw.polygon(screen, (255, 255, 255), arrow_points)
    
    dropdown_rect = pygame.Rect(x, y, w, h)
    option_rects = []
    
    if open_dropdown:
        for i, opt in enumerate(options):
            opt_rect = pygame.Rect(x, y + (i + 1) * h, w, h)
            bg_color = (100, 100, 160) if i == selected_idx else (80, 80, 120)
            pygame.draw.rect(screen, bg_color, opt_rect, border_radius=6)
            
            opt_label = font.render(opt, True, (255, 255, 255))
            screen.blit(opt_label, (x + 10, y + (i + 1) * h + h//4))
            option_rects.append(opt_rect)
    
    return dropdown_rect, option_rects

def check_collision(body1, body2):
    """Check if two bodies are colliding"""
    dx = body1.x - body2.x
    dy = body1.y - body2.y
    dist = math.hypot(dx, dy)
    return dist < body1.radius + body2.radius

def check_neutron_star_collision(body1, body2):
    """Check if two neutron stars are colliding"""
    if body1.body_type == "neutron_star" and body2.body_type == "neutron_star":
        return check_collision(body1, body2)
    return False

def render_text_with_colored_numbers(text, font, x, y, screen):
    words = text.split(' ')
    cursor_x = x

    for word in words:
        if any(char.isdigit() for char in word):
            surf = font.render(word, True, (0, 200, 0))
        else:
            surf = font.render(word, True, (255, 255, 255))
        screen.blit(surf, (cursor_x, y))
        cursor_x += surf.get_width() + 6  # Add spacing

def draw_ui_info(screen, bodies, particles, theory):
    """Draw information panel"""
    font = pygame.font.Font(None, 24)
    
    # Count different body types
    planets = sum(1 for b in bodies if b.body_type == "planet")
    stars = sum(1 for b in bodies if b.body_type == "star")
    neutron_stars = sum(1 for b in bodies if b.body_type == "neutron_star")
    black_holes = sum(1 for b in bodies if b.body_type == "black_hole")
    total_mass = sum(b.mass for b in bodies) + sum(p.mass for p in particles.particles)
    
    info_texts = [
        f"Planets: {planets}",
        f"Stars: {stars}",
        f"Neutron Stars: {neutron_stars}",
        f"Black Holes: {black_holes}",
        f"Particles: {len(particles.particles)}",
        f"Theory: {theory}",
        f"FPS: {int(clock.get_fps())}"
    ]
    info_texts.append(f"Total Universe Mass: {total_mass:.2e}")
    
    for i, text in enumerate(info_texts):
        color = (255, 255, 255)  # default white

        if "Black Holes" in text and black_holes > 0:
            color = (200, 100, 200)
        elif "Neutron Stars" in text and neutron_stars > 0:
            color = (200, 200, 255)
        elif "Stars" in text and stars > 0:
            color = (255, 255, 100)
        elif "Total Universe Mass" in text:
            color = (255, 180, 255)
        elif any(char.isdigit() for char in text):
            color = (0, 200, 0)  # only apply if none of the above matched

        
        render_text_with_colored_numbers(text,font, WIDTH-250, 50+i*25,screen)

def draw_checkbox(screen, x, y, size, checked, label):
    """Draw a checkbox with a label and return its rect"""
    box_rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(screen, (200, 200, 200), box_rect, 2)
    if checked:
        pygame.draw.rect(screen, (100, 255, 100), box_rect.inflate(-6, -6))
    font = pygame.font.Font(None, 24)
    label_surf = font.render(label, True, (255, 255, 255))
    screen.blit(label_surf, (x + size + 10, y + size // 4))
    return box_rect

def draw_spacetime_grid(screen, bodies, color=(100, 255, 255)):
    """Draw a spacetime grid that curves locally into massive objects (gravity wells)."""
    grid_spacing = 60
    for x in range(0, WIDTH, grid_spacing):
        points = []
        for y in range(0, HEIGHT - 200, 8):
            local_warp = 0
            for b in bodies:
                dx = x - b.x
                dy = y - b.y
                dist = math.hypot(dx, dy)
                if dist < 1: dist = 1
                local_warp += b.mass / (dist * 2)
            # Subtract local_warp to curve into the mass
            offset = int(-local_warp)
            points.append((x + offset, y))
        pygame.draw.lines(screen, color, False, points, 1)
    for y in range(0, HEIGHT - 200, grid_spacing):
        points = []
        for x in range(0, WIDTH, 8):
            local_warp = 0
            for b in bodies:
                dx = x - b.x
                dy = y - b.y
                dist = math.hypot(dx, dy)
                if dist < 1: dist = 1
                local_warp += b.mass / (dist * 2)
            # Subtract local_warp to curve into the mass
            offset = int(-local_warp)
            points.append((x, y + offset))
        pygame.draw.lines(screen, color, False, points, 1)

def draw_inspect_panel(screen, obj):
    font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)
    panel_w, panel_h = 390, 310
    x, y = 40, 60
    pygame.draw.rect(screen, (30, 30, 60), (x, y, panel_w, panel_h), border_radius=10)
    # Info
    info = [
        f"Type: {getattr(obj, 'body_type', 'particle')}",
        f"Mass: {obj.mass:.2f}",
        f"Radius: {getattr(obj, 'radius', '-')}",
        f"Pos: ({obj.x:.1f}, {obj.y:.1f})",
        f"Vel: ({getattr(obj, 'vx', 0):.2f}, {getattr(obj, 'vy', 0):.2f})",
        f"Age: {getattr(obj, 'age', 0)}",
        f"Net force: ({getattr(obj, 'last_force', (0,0))[0]:.2f}, {getattr(obj, 'last_force', (0,0))[1]:.2f})"
    ]
    for i, line in enumerate(info):
        screen.blit(font.render(line, True, (255,255,255)), (x+16, y+20+i*28))
    # Mass chart
    chart_x, chart_y = x+10, y+230
    chart_w, chart_h = 320, 70
    pygame.draw.rect(screen, (50, 50, 90), (chart_x, chart_y, chart_w, chart_h), border_radius=6)
    if hasattr(obj, 'mass_history') and len(obj.mass_history) > 1:
        points = []
        min_mass = min(m for _, m in obj.mass_history)
        max_mass = max(m for _, m in obj.mass_history)
        min_age = min(a for a, _ in obj.mass_history)
        max_age = max(a for a, _ in obj.mass_history)
        for age, mass in obj.mass_history:
            px = chart_x + int((age-min_age)/(max(1,max_age-min_age))*chart_w)
            if max_mass-min_mass > 0:
                py = chart_y + chart_h - int((mass-min_mass)/(max_mass-min_mass)*chart_h)
            else:
                py = chart_y + chart_h//2
            points.append((px, py))
        if len(points) > 1:
            pygame.draw.lines(screen, (100,255,100), False, points, 2)
        # Axis
        screen.blit(small_font.render(f"Mass over time", True, (200,255,200)), (chart_x+4, chart_y+2))
        screen.blit(small_font.render(f"{min_mass:.1f}", True, (200,200,200)), (chart_x+4, chart_y+chart_h-18))
        screen.blit(small_font.render(f"{max_mass:.1f}", True, (200,200,200)), (chart_x+4, chart_y+8))

def pSound(sound_paths, loaded_sounds=None):
    # Load sounds once if not already loaded
    if loaded_sounds is None:
        loaded_sounds = [pygame.mixer.Sound(path) for path in sound_paths]

    # Pick and play a random sound
    sound = random.choice(loaded_sounds)
    sound.play()
    print(f"Played: {sound_paths[loaded_sounds.index(sound)]}")  # Show which sound was played

    return loaded_sounds  # Return the loaded sounds so you can reuse them next time

def notification(screen, text, duration=2):
    """Display a notification message on the screen for a limited time."""
    font = pygame.font.Font(None, 36)
    text_surf = font.render(text, True, (255, 255, 100))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    pygame.display.flip()
    pygame.time.delay(int(duration * 1000))  # Convert to milliseconds

import pygame
import random

def play_random_sounds(sound_paths, state):
    # Load sounds + paths on first run
    if "sounds" not in state:
        state["sounds"] = [(path, pygame.mixer.Sound(path)) for path in sound_paths]
        state["playing"] = False
        state["last_end_time"] = 0

    now = pygame.time.get_ticks()

    if not state["playing"]:
        path, sound = random.choice(state["sounds"])
        sound.play()
        state["last_end_time"] = now + int(sound.get_length() * 1000)
        state["playing"] = True
        state["current_path"] = path  # store current playing path
        print(f"Now playing: {path}")  # 🎶 Print the path!

    elif now >= state["last_end_time"]:
        state["playing"] = False

def eject_particles(x, y, vx, vy, mass_loss, particle_system, body_type="star"):
    max_particles = 1  # 🎯 Feel free to tweak this!
    num_particles = min(max_particles, max(1, int(mass_loss // 1.5)))
    particle_mass = mass_loss / num_particles


    # Adjust spawn offset
    spawn_radius = 25  # This pushes particles beyond the consumption radius

    for _ in range(num_particles):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)

        # Spawn outside body radius
        px = x + math.cos(angle) * spawn_radius
        py = y + math.sin(angle) * spawn_radius

        px_vx = vx + math.cos(angle) * speed
        px_vy = vy + math.sin(angle) * speed

        if body_type == "star":
            color = (255, 200, 100)
        elif body_type == "neutron_star":
            color = (180, 180, 255)
        else:
            color = (255, 255, 255)

        particle_system.particles.append(Particle(px, py, px_vx, px_vy, color, mass=particle_mass))

def main():
    global checkbox_rect, big_bang_checkbox_rect, execute_rect_list
    bodies = []
    particle_system = ParticleSystem()
    running = True
    paused = False
    inspect_mode = False
    inspected_obj = None

    # UI setup
    font = pygame.font.Font(None, 28)
    instructions = font.render("Left click/drag: Add planet | Right click: Add star | ESC: Quit", True, (255, 255, 255))
    
    # Parameters
    planet_mass = 10.0
    min_mass, max_mass = 1, 100
    star_mass = 150.0
    min_star_mass, max_star_mass = 50, 500
    
    # UI state
    dragging_mass = False
    dragging_star_mass = False
    spacetime_grid_enabled = False
    
    # Inspect and pause UI state
    inspect_mode = False
    mass_histories = collections.defaultdict(list)  # id(obj) -> [mass]
    pause_button_rect = pygame.Rect(WIDTH - 200, HEIGHT - 60, 120, 40)
    inspect_button_rect = pygame.Rect(WIDTH - 340, HEIGHT - 60, 120, 40)
    trajectory_button_rect = pygame.Rect(WIDTH - 200, HEIGHT - 110, 120, 40)
    # Time lapse state
    time_lapse_multiplier = 1
    max_time_lapse = 5
    time_lapse_button_rect = pygame.Rect(WIDTH - 340, HEIGHT - 110, 120, 40)

    # UI layout
    UI_BAR_HEIGHT = 200
    # Move all UI elements to the left
    left_col_x = 40
    left_col_w = 300
    # Increase vertical spacing between sliders
    planet_slider_y = HEIGHT - 120
    star_slider_y = HEIGHT - 70 + 10
    right_col_x = 40
    slider_h = 20
    # Dropdown box stays in its original position
    # (dropdown_x, dropdown_y, dropdown_w, dropdown_h are unchanged)
    dropdown_x, dropdown_y, dropdown_w, dropdown_h = 550, HEIGHT - 140, 260, 40
    theory_options = ["Newtonian", "General Relativity"]
    selected_theory = 0
    open_dropdown = False

    loaded_Sounds = None
    
    # Spawn mechanics
    spawn_start = None
    spawn_end = None
    dragging_spawn = False
    
    # Spawn mode state
    isSpawningPlanets = True  # Start with planet spawn mode
    isSpawningStars = False  # Start with star spawn mode
    isSpawningParticles = False  # Start with particle spawn mode

    # Add black hole checkbox state
    black_hole_mode = False

    # Black hole mass range (tweak as needed)
    min_bh_mass, max_bh_mass = 650, 2000

    # Trajectory toggle state
    show_trajectories = True
    # Simulation time (in years)
    sim_year = 0.0
    years_per_frame = 0.05  # Tune for how fast time passes

    # Add big bang checkbox state
    big_bang_mode = False
    big_bang_events = []  # List of (x, y, timer) for ongoing big bangs

    execute_rect_list = []

    projectInfo = False

    # Category UI state
    categories = ["main", "creation", "settings", "utilities","Power"]
    current_category = "main"
    # Scroll offsets for each category (for horizontal scrolling)
    category_scroll = {cat: 0 for cat in categories}
    scroll_step = 120  # How much to scroll per click

    while running:
        
        play_random_sounds(musicBackgroundListPath, scrapedSounds)

        # Initialize all UI rects to None at the start of each frame
        checkbox_rect = None
        big_bang_checkbox_rect = None
        knob_rect = None
        star_knob_rect = None
        dropdown_rect = None
        option_rects = None
        grid_checkbox_rect = None
        return_rect = None
        clear_button_rect = None  # Ensure clear_button_rect is always defined
        spawn_Planet_button = None
        spawn_Stars_button = None
        execute_black_hole_btn_rect = None
        execute_neutron_star_btn_rect = None
        execute_planets_btn_rect = None
        execute_stars_btn_rect = None
        clicked_ui = None

        # Clear screen
        screen.fill((10, 10, 30))
        if theory_options[selected_theory] == "General Relativity" and spacetime_grid_enabled:
            draw_spacetime_grid(screen, bodies)

        
        # Draw instructions
        screen.blit(instructions, (20, 20))
        
        # Draw UI info
        if projectInfo:
            draw_ui_info(screen, bodies, particle_system, theory_options[selected_theory])
        
        # Draw current simulation year at top right
        font_year = pygame.font.Font(None, 36)
        year_text = f"Year: {int(sim_year)}"
        screen.blit(font_year.render(year_text, True, (255,255,180)), (WIDTH - 220, 10))
        
        # Draw bottom UI bar
        pygame.draw.rect(screen, (30, 30, 50), (0, HEIGHT - UI_BAR_HEIGHT, WIDTH, UI_BAR_HEIGHT))

        # Draw category navigation buttons below info
        cat_btns = ["Creation", "Settings", "Utilities","Power"]
        cat_btn_rects = []
        btn_w, btn_h = 160, 38
        btn_y = HEIGHT - UI_BAR_HEIGHT

        for idx, cat in enumerate(cat_btns):
            btn_x = idx * (btn_w + 5)
            rect = draw_button(screen, btn_x, btn_y, btn_w, btn_h, cat)
            cat_btn_rects.append((cat.lower(), rect))
        # No utility buttons in main category

        pygame.draw.line(screen, (100,100,150), (0, HEIGHT - UI_BAR_HEIGHT + 38 + 5), (WIDTH, HEIGHT - UI_BAR_HEIGHT + 38 + 5), 2)
        pygame.draw.line(screen, (100,100,150), (140, 492), (140, 649),2)

        # --- CATEGORY NAVIGATION ---
        if current_category == "main":
            # --- REWORKED MAIN CATEGORY UI ---
            # Draw a large, visually appealing info panel in the center
            info_panel_x = WIDTH // 2 - 260
            info_panel_y = HEIGHT - UI_BAR_HEIGHT + 38 + 15
            info_panel_w = 480
            info_panel_h = 120
            pygame.draw.rect(screen, (50, 60, 90), (info_panel_x, info_panel_y, info_panel_w, info_panel_h), border_radius=18)
            font = pygame.font.Font(None, 38)
            planets = sum(1 for b in bodies if b.body_type == "planet")
            stars = sum(1 for b in bodies if b.body_type == "star")
            neutron_stars = sum(1 for b in bodies if b.body_type == "neutron_star")
            black_holes = sum(1 for b in bodies if b.body_type == "black_hole")
            total_mass = sum(b.mass for b in bodies) + sum(p.mass for p in particle_system.particles)
            info_texts = [
                f"Planets: {planets}",
                f"Stars: {stars}",
                f"Neutron Stars: {neutron_stars}",
                f"Black Holes: {black_holes}",
                f"Particles: {len(particle_system.particles)}",
                f"FPS: {int(clock.get_fps())}"
            ]
            # Draw "Total Universe Mass" label next to the info panel
            font_mass = pygame.font.Font(None, 36)
            mass_text = f"Total Universe Mass: {int(total_mass)}"
            mass_color = (255, 180, 255)
            mass_label = font_mass.render(mass_text, True, mass_color)

            # Position: to the right of the panel
            mass_x = info_panel_x + info_panel_w + 30
            mass_y = info_panel_y + 20

            screen.blit(mass_label, (mass_x, mass_y))
            for i, text in enumerate(info_texts):
                color = (255, 255, 255)
                if "Black Holes" in text and black_holes > 0:
                    color = (200, 100, 200)
                elif "Neutron Stars" in text and neutron_stars > 0:
                    color = (200, 200, 255)
                elif "Stars" in text and stars > 0:
                    color = (255, 255, 100)
                text_surf = font.render(text, True, color)
                screen.blit(text_surf, (info_panel_x + 32 + (i%2)*240, info_panel_y + 12 + (i//2)*36))
        else:
            # Draw Return button
            return_rect = draw_button(screen, 10, HEIGHT-UI_BAR_HEIGHT+38+15, 120, 120, "Return")
            if current_category == "creation":
                # Sliders and checkboxes
                base_x = 140 + 10 + 135 + 20
                slider_rect, knob_rect = draw_slider(
                    screen, base_x, planet_slider_y, left_col_w, slider_h,
                    min_mass, max_mass, planet_mass, "Planet mass"
                )
                star_slider_rect, star_knob_rect = draw_slider(
                    screen, base_x, star_slider_y, left_col_w, slider_h,
                    min_star_mass if not black_hole_mode else min_bh_mass,
                    max_star_mass if not black_hole_mode else max_bh_mass,
                    star_mass, "Star mass", color=(255, 255, 100)
                )

                spawn_Planet_button = draw_button(
                    screen, base_x - 135 - 10, planet_slider_y - 25, 135, 50, "Planel Spawn", isSpawningPlanets
                )

                spawn_Stars_button = draw_button(
                    screen, base_x - 135 - 10, star_slider_y - 20, 135, 50, "Stars Spawn", isSpawningStars
                )

                checkbox_rect = draw_checkbox(
                    screen, base_x + left_col_w + 30, star_slider_y, 24, black_hole_mode, "black hole"
                )
                big_bang_checkbox_rect = draw_checkbox(
                    screen, base_x + left_col_w + 30, planet_slider_y, 24, big_bang_mode, "big bang"
                )
            elif current_category == "settings":
                # Dropdown and spacetime grid
                base_x = 140 + 10
                dropdown_rect, option_rects = draw_dropdown(
                    screen, base_x, HEIGHT - 140, dropdown_w, dropdown_h,
                    theory_options, selected_theory, open_dropdown
                )
                if theory_options[selected_theory] == "General Relativity":
                    grid_checkbox_rect = draw_checkbox(
                        screen, base_x + dropdown_w + 40, HEIGHT - 140, 24, spacetime_grid_enabled, "spacetime grid"
                    )
                else:
                    grid_checkbox_rect = None
                font2 = pygame.font.Font(None, 24)
                screen.blit(font2.render("Gravity Theory:", True, (255, 255, 255)), 
                           (base_x, HEIGHT - 168))
            elif current_category == "utilities":
                # Pause/Resume, Inspect, Trajectory, Time Lapse, Clear
                base_x = 230
                btn_w, btn_h = 180, 48
                gap_x, gap_y = 40, 18
                # 2x2 grid
                
                inspect_button_rect = draw_button(
                    screen, base_x, HEIGHT - 140, btn_w, btn_h, "Inspect", active=inspect_mode
                )
                pause_button_rect = draw_button(
                    screen, base_x + btn_w + gap_x, HEIGHT - 140, btn_w, btn_h, "Pause" if not paused else "Resume", active=paused
                )
                trajectory_button_rect = draw_button(
                    screen, base_x, HEIGHT - 140 + btn_h + gap_y, btn_w, btn_h, "Trajectory", active=show_trajectories
                )

                clear_button_rect = draw_button(
                    screen, base_x + btn_w + gap_x, HEIGHT - 140 + btn_h + gap_y, btn_w, btn_h, "Clear"
                )
                time_lapse_button_rect = draw_button(screen, base_x + (btn_w + gap_x)*2, HEIGHT - 140, btn_w, btn_h, f"Speed: {time_lapse_multiplier}x")  # Remove time lapse button from utilities

            elif current_category == "power":
                base_x = 230
                gap_x, gap_y = 40, 18
                primaryRowY = HEIGHT - 140
                secondaryRowY = primaryRowY + btn_h + gap_y
                spacer = btn_w + gap_x


                execute_planets_btn_rect = draw_button(
                    screen, base_x, primaryRowY, btn_w, btn_h, "Exe. Planet"
                )

                execute_stars_btn_rect = draw_button(
                    screen, base_x, secondaryRowY, btn_w, btn_h, "Exe. Stars"
                )

                execute_neutron_star_btn_rect = draw_button(
                    screen, base_x + spacer, primaryRowY, btn_w, btn_h, "Exe. Neutron stars"
                )

                execute_black_hole_btn_rect = draw_button(
                    screen, base_x + spacer, secondaryRowY, btn_w, btn_h, "Exe. Black Holes"
                )

                execute_rect_list = [("black_hole",execute_black_hole_btn_rect),
                                     ("neutron_star",execute_neutron_star_btn_rect),
                                     ("star",execute_stars_btn_rect),
                                     ("planet",execute_planets_btn_rect)
                ]

            else:
                pass
        # --- CATEGORY EVENT HANDLING ---
        for event in pygame.event.get():
            mx, my = pygame.mouse.get_pos()
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Clear all bodies and particles
                    bodies.clear()
                    particle_system.particles.clear()
                if event.key == pygame.K_o:
                    projectInfo = not projectInfo
                if event.key == pygame.K_c:
                    bodies.clear()
                    particle_system.particles.clear()
                if event.key == pygame.K_i:
                    show_trajectories = not show_trajectories
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_m:
                    inspect_mode = not inspect_mode
                if event.key == pygame.K_LEFT:
                    time_lapse_multiplier = time_lapse_multiplier % max_time_lapse + 1
                if event.key == pygame.K_RIGHT:
                    time_lapse_multiplier = time_lapse_multiplier % max_time_lapse - 1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle category button clicks
                for cat, rect in cat_btn_rects:
                    if rect.collidepoint(mx, my):
                        current_category = cat
                        break
                # Prevent utility buttons from being active in main
                if current_category == "main":
                    inspect_button_rect = None
                    pause_button_rect = None
                    trajectory_button_rect = None
                    time_lapse_button_rect = None
                mx, my = pygame.mouse.get_pos()
                if "main" in categories:
                    categories.remove("main")
                else:
                    pass
                for items in categories:
                    if current_category != items:
                        continue
                    else:
                        if return_rect is None:
                            return_rect = draw_button(screen, 10, HEIGHT-UI_BAR_HEIGHT+38+15, 120, 120, "Return")
                            if return_rect.collidepoint(mx, my):
                                current_category = "main"
                                continue
                        else:
                            # Handle Return button
                            if return_rect and return_rect.collidepoint(mx, my):
                                current_category = "main"
                                continue
                        # Handle Inspect, Pause/Resume, Trajectory, and Clear button clicks (utilities)
                        if current_category == "utilities":
                            if inspect_button_rect and inspect_button_rect.collidepoint(mx, my):
                                inspect_mode = not inspect_mode
                                inspected_obj = None
                                continue
                            elif inspect_button_rect is None:
                                print("inspect_button_rect is none")
                            if pause_button_rect and pause_button_rect.collidepoint(mx, my):
                                paused = not paused
                                continue
                            elif pause_button_rect is None:
                                print("pause_button_rect is none")
                            if trajectory_button_rect and trajectory_button_rect.collidepoint(mx, my):
                                show_trajectories = not show_trajectories
                                continue
                            elif trajectory_button_rect is None:
                                print("trajectory_button_rect is none")
                            if clear_button_rect and clear_button_rect.collidepoint(mx, my):
                                bodies.clear()
                                particle_system.particles.clear()
                                continue
                            elif clear_button_rect is None:
                                print("clear_button_rect is none")
                            if time_lapse_button_rect and time_lapse_button_rect.collidepoint(mx, my):
                                time_lapse_multiplier = time_lapse_multiplier % max_time_lapse + 1
                if theory_options[selected_theory] == "General Relativity" and grid_checkbox_rect and event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and grid_checkbox_rect.collidepoint(mx, my):
                        spacetime_grid_enabled = not spacetime_grid_enabled
                if current_category == "settings":
                    # Handle dropdown selection
                    if dropdown_rect and dropdown_rect.collidepoint(mx, my):
                        open_dropdown = not open_dropdown
                    # Handle option selection in dropdown
                    if open_dropdown and option_rects:
                        for idx, opt_rect in enumerate(option_rects):
                            if opt_rect.collidepoint(mx, my):
                                selected_theory = idx
                                open_dropdown = False
                                break
                if event.button == 1:  # Left click
                    if current_category == "main":
                        if pygame.Rect(info_panel_x, info_panel_y, info_panel_w, info_panel_h).collidepoint(mx, my):
                            projectInfo = not projectInfo
                    if current_category == "creation":
                        clicked_ui = False
                        if knob_rect and knob_rect.collidepoint(mx, my):
                            dragging_mass = True
                            clicked_ui = True
                        elif star_knob_rect and star_knob_rect.collidepoint(mx, my):
                            dragging_star_mass = True
                            clicked_ui = True
                        if checkbox_rect and checkbox_rect.collidepoint(mx, my):
                            black_hole_mode = not black_hole_mode
                            # Snap star_mass into new range if needed
                            if black_hole_mode:
                                star_mass = max(star_mass, min_bh_mass)
                            else:
                                star_mass = min(star_mass, max_star_mass)
                            clicked_ui = True
                        if big_bang_checkbox_rect and big_bang_checkbox_rect.collidepoint(mx, my):
                            big_bang_mode = not big_bang_mode
                            clicked_ui = True
                        if spawn_Planet_button and spawn_Planet_button.collidepoint(mx,my):
                            if (isSpawningParticles, isSpawningStars) == (False, False):
                                isSpawningPlanets = not isSpawningPlanets
                            elif (isSpawningParticles, isSpawningStars) == (False, True):
                                isSpawningStars = not isSpawningStars
                                isSpawningPlanets = not isSpawningPlanets
                        elif spawn_Stars_button and spawn_Stars_button.collidepoint(mx,my):
                            if (isSpawningPlanets, isSpawningParticles) == (False, False):
                                isSpawningStars = not isSpawningStars
                            elif (isSpawningPlanets, isSpawningParticles) == (True, False):
                                isSpawningPlanets = not isSpawningPlanets
                                isSpawningStars = not isSpawningStars
                        elif isSpawningPlanets == False and isSpawningStars == False:
                            isSpawningParticles = True
                        if not clicked_ui and my < HEIGHT - UI_BAR_HEIGHT:
                            if big_bang_mode:
                                # Remove and explode any black hole at/near the big bang location
                                bh_indices = [i for i, b in enumerate(bodies) if b.body_type == "black_hole" and math.hypot(mx - b.x, my - b.y) < 60]
                                for i in reversed(bh_indices):
                                    bh = bodies[i]
                                    num_particles = min(100, int(bh.mass * 2))
                                    for _ in range(num_particles):
                                        angle = random.uniform(0, 2 * math.pi)
                                        speed = random.uniform(3, 8)
                                        vx = bh.vx + math.cos(angle) * speed
                                        vy = bh.vy + math.sin(angle) * speed
                                        color = (255, 100, 100)
                                        particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=bh.mass/num_particles))
                                    bodies.pop(i)
                                big_bang_events.append({'x': mx, 'y': my, 'timer': 0})
                            else:
                                spawn_start = (mx, my)
                                spawn_end = (mx, my)
                                dragging_spawn = True
                    if current_category == "power":
                        for btype,button in execute_rect_list:
                            if button and button.collidepoint(mx, my):
                                obj_indices = [i for i, b in enumerate(bodies) if b.body_type == btype]
                                for i in reversed(obj_indices):
                                    obj = bodies[i]
                                    num_particles = round(obj.mass/3)
                                    for _ in range(num_particles):
                                        angle = random.uniform(0, 2 * math.pi)
                                        speed = random.uniform(3, 8)
                                        vx = obj.vx + math.cos(angle) * speed
                                        vy = obj.vy + math.sin(angle) * speed
                                        color = (255, 100, 100)
                                        particle_system.particles.append(Particle(obj.x, obj.y, vx, vy, color, 2))
                                    bodies.pop(i)
                                    loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                    elif inspect_mode and my < HEIGHT - UI_BAR_HEIGHT:
                        # Try to select an object
                        found = False
                        for b in bodies:
                            if math.hypot(mx-b.x, my-b.y) < b.radius+6:
                                inspected_obj = b
                                found = True
                                break
                        if not found:
                            for p in particle_system.particles:
                                if math.hypot(mx-p.x, my-p.y) < 8:
                                    inspected_obj = p
                                    found = True
                                    break
                        if not found:
                            inspected_obj = None
                    elif my < HEIGHT - UI_BAR_HEIGHT:
                        if big_bang_mode:
                            # Remove and explode any black hole at/near the big bang location
                            bh_indices = [i for i, b in enumerate(bodies) if b.body_type == "black_hole" and math.hypot(mx - b.x, my - b.y) < 60]
                            for i in reversed(bh_indices):
                                bh = bodies[i]
                                # Explode black hole into particles (supernova-like)
                                num_particles = min(100, int(bh.mass * 2))
                                for _ in range(num_particles):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed = random.uniform(3, 8)
                                    vx = bh.vx + math.cos(angle) * speed
                                    vy = bh.vy + math.sin(angle) * speed
                                    color = (255, 100, 100)
                                    particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=bh.mass/num_particles))
                            big_bang_events.append({'x': mx, 'y': my, 'timer': 0})
                        else:
                            spawn_start = (mx, my)
                            spawn_end = (mx, my)
                            dragging_spawn = True
            elif event.type == pygame.MOUSEBUTTONUP:
                mx, my = pygame.mouse.get_pos()
                
                if event.button == 1:
                    if dragging_mass:
                        dragging_mass = False
                    elif dragging_star_mass:
                        dragging_star_mass = False
                    if dragging_spawn and spawn_start:
                        spawn_end = (mx, my)
                        dx = spawn_end[0] - spawn_start[0]
                        dy = spawn_end[1] - spawn_start[1]
                        drag_dist = math.hypot(dx, dy)
                        min_drag = -1  # Minimum drag distance to spawn
                
                        if isSpawningParticles:
                            if drag_dist > min_drag:
                                velocity_scale = 0.05
                                vx = dx * velocity_scale
                                vy = dy * velocity_scale
                                color = random_color()
                                mass = random.uniform(0.1, 5.0)
                                particle_system.particles.append(Particle(spawn_start[0], spawn_start[1], vx, vy, color, mass=mass))
                            isSpawningParticles = False  # Reset mode so buttons work again
                
                        elif isSpawningPlanets or isSpawningStars:
                            if drag_dist > min_drag:
                                velocity_scale = 0.05
                                vx = dx * velocity_scale
                                vy = dy * velocity_scale
                                if isSpawningPlanets:
                                    mass = planet_mass
                                    radius = max(3, int(mass))
                                    color = random_color()
                                    body_type = "planet"
                                elif isSpawningStars and not black_hole_mode:
                                    mass = star_mass
                                    radius = max(8, int(mass ** 0.4)) if mass < 350 else max(8, int(mass ** 0.2))
                                    color = (255,255,100) if mass < 350 else (200,200,255)
                                    body_type = "star" if mass < 350 else "neutron_star"
                                elif isSpawningStars and black_hole_mode:
                                    mass = star_mass
                                    radius = max(10, int(mass ** 0.3))
                                    color = (50, 0, 50)
                                    body_type = "black_hole"
                                    
                                body = Body(spawn_start[0], spawn_start[1], mass, radius, color, body_type)
                                body.vx = vx
                                body.vy = vy
                                bodies.append(body)
                
                        # Always reset drag state
                        dragging_spawn = False
                        spawn_start = None
                        spawn_end = None                  
                if open_dropdown and not dropdown_rect.collidepoint(mx, my):
                    open_dropdown = False
            elif event.type == pygame.MOUSEMOTION:
                mx, my = pygame.mouse.get_pos()
                if current_category == "creation":
                    base_x = 305 - category_scroll[current_category]  # This matches your draw_slider call!
                    if dragging_star_mass:
                        rel_x = max(base_x, min(mx, base_x + left_col_w))
                        if black_hole_mode:
                            star_mass = (rel_x - base_x) / left_col_w * (max_bh_mass - min_bh_mass) + min_bh_mass
                        else:
                            star_mass = (rel_x - base_x) / left_col_w * (max_star_mass - min_star_mass) + min_star_mass
                
                    elif dragging_mass:
                        rel_x = max(base_x, min(mx, base_x + left_col_w))
                        planet_mass = (rel_x - base_x) / left_col_w * (max_mass - min_mass) + min_mass
                if dragging_spawn and spawn_start:
                    spawn_end = (mx, my)
            
        # Draw arrow for planet spawn drag (only if dragging_spawn)
        if dragging_spawn and spawn_start and spawn_end:
            arrow_color = (100, 255, 100)
            pygame.draw.line(screen, arrow_color, spawn_start, spawn_end, 4)
            # Draw arrowhead
            dx = spawn_end[0] - spawn_start[0]
            dy = spawn_end[1] - spawn_start[1]
            angle = math.atan2(dy, dx)
            length = math.hypot(dx, dy)
            if length > 10:
                head_len = 18
                head_angle = math.pi / 7
                for sign in [-1, 1]:
                    hx = spawn_end[0] - head_len * math.cos(angle - sign * head_angle)
                    hy = spawn_end[1] - head_len * math.sin(angle - sign * head_angle)
                    pygame.draw.line(screen, arrow_color, spawn_end, (hx, hy), 4)

        # Update simulation time (year) regardless of pause
        sim_year += years_per_frame * time_lapse_multiplier

        # Update physics (skip if paused)
        if not paused:
            particle_system.update(bodies,time_lapse_multiplier)
            particle_system.try_combine_particles(bodies)
            for body in bodies:
                body.update(bodies, particle_system, theory_options[selected_theory], time_lapse_multiplier)
                # Track mass history for inspect
                mass_histories[id(body)].append(body.mass)
                if len(mass_histories[id(body)]) > 120:
                    mass_histories[id(body)] = mass_histories[id(body)][-120:]
            # Track mass for selected particle
            for p in particle_system.particles:
                mass_histories[id(p)].append(p.mass)
                if len(mass_histories[id(p)]) > 120:
                    mass_histories[id(p)] = mass_histories[id(p)][-120:]

        # After updating bodies
        evaporated_bhs = []
        for i, body in enumerate(bodies):
            if body.body_type == "black_hole" and body.evaporate():
                evaporated_bhs.append(i)
        
        for i in reversed(evaporated_bhs):
            bh = bodies[i]
            fate = random.random()
            if fate < 1:
                print("DEBUG: Bh Case 1 Initialized")
                # Case 1: Explode into supernova-like particles
                particles = []
                num_particles = min(100, int(bh.mass * 2))
                for _ in range(num_particles):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(3, 8)
                    vx = bh.vx + math.cos(angle) * speed
                    vy = bh.vy + math.sin(angle) * speed
                    color = (255, 100, 100)
                    particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=bh.mass/num_particles))
                particle_system.particles.extend(particles)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif fate < 0.2:
                # Case 2: Collapse into neutron star, release strong wave of particles
                ns_mass = max(10, bh.mass * 0.7)
                ns_radius = max(8, int(ns_mass ** 0.2))
                ns = Body(bh.x, bh.y, ns_mass, ns_radius, (200, 200, 255), "neutron_star")
                ns.vx, ns.vy = bh.vx, bh.vy
                bodies.append(ns)
                # Release wave particles
                for _ in range(80):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(6, 12)
                    vx = bh.vx + math.cos(angle) * speed
                    vy = bh.vy + math.sin(angle) * speed
                    color = (100, 200, 255)
                    particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=1))
                print("DEBUG: Bh Case 2 Intiallized")
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            else:
                print("DEBUG: Bh Case 3 Initialized")
                # Case 3: Shoot out particles until no mass left
                num_particles = int(bh.mass)
                for _ in range(num_particles):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(8, 16)
                    vx = bh.vx + math.cos(angle) * speed
                    vy = bh.vy + math.sin(angle) * speed
                    color = (255, 255, 255)
                    particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=1))
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)

            # Remove the black hole
            bodies.pop(i)
        
        # Handle stellar consumption of particles and planets
        particles_to_remove = []
        for i, particle in enumerate(particle_system.particles):
            for body in bodies:
                if body.can_consume(particle):
                    body.consume(particle)
                    particles_to_remove.append(i)
                    break
        
        # Remove consumed particles (in reverse order to maintain indices)
        for i in reversed(particles_to_remove):
            particle_system.particles.pop(i)
        
        bodies_to_remove = set()
        # Check for planet-to-star collapse, star/neutron star collapse, and star/neutron star explosion
        collapse_explosions = []
        new_bodies = []
        for i, body in enumerate(bodies):
            collapse_type = body.should_collapse()
            # Prevent black hole formation during big bang event
            if big_bang_mode and collapse_type == "neutron_to_bh":
                continue
            if collapse_type == "planet_to_star":
                particles = body.collapse_to_star()
                collapse_explosions.extend(particles)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif collapse_type == "star_to_neutron":
                if random.random() < 0.7:
                    particles = body.collapse_to_neutron_star()
                    collapse_explosions.extend(particles)
                    loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                else:
                    particles = body.explode_to_supernova()
                    collapse_explosions.extend(particles)
                    bodies_to_remove.add(i)
                    loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif collapse_type == "star_to_particles":
                particles, planets = body.explode_to_particles_and_planets()
                collapse_explosions.extend(particles)
                new_bodies.extend(planets)
                bodies_to_remove.add(i)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif collapse_type == "neutron_to_bh":
                if random.random() < 0.5:
                    body.body_type = "black_hole"
                    body.radius = max(10, int(body.mass ** 0.3))
                    body.color = (50, 0, 50)
                    body.consumption_radius = body.radius * 3
                    loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                    print("DEBUG: N>>>Bh")
                else:
                    print("DEBUG: N>>>Bh Cancelled")
                    particles = body.explode_to_supernova()
                    collapse_explosions.extend(particles)
                    bodies_to_remove.add(i)
                    loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif collapse_type == "neutron_to_particles":
                particles, planets = body.explode_to_particles_and_planets()
                collapse_explosions.extend(particles)
                new_bodies.extend(planets)
                bodies_to_remove.add(i)
                print("DEBUG: N>>>p")
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
            elif collapse_type == "trigger_supernova":
                particles = body.explode_to_supernova()
                collapse_explosions.extend(particles)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                collapse_explosions.extend(particles)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                collapse_explosions.extend(particles)
                loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
                bodies_to_remove.add(i)


        # Handle stellar consumption of smaller bodies
        for i, body1 in enumerate(bodies):
            for j, body2 in enumerate(bodies):
                if body1.body_type != "planet" or body2.body_type != "planet":
                    if i != j and i not in bodies_to_remove and j not in bodies_to_remove:
                        if body1.can_consume(body2) and body1.mass > body2.mass:
                            body1.consume(body2)
                            bodies_to_remove.add(j)
                            print("checked")

        def directional_explosion(bigger, smaller, num_particles=40, mass=2):
            loaded_Sounds = None
            dx = smaller.x - bigger.x
            dy = smaller.y - bigger.y
            impact_angle = math.atan2(dy, dx)
            print(num_particles)
            for _ in range(num_particles):
                spread = random.uniform(-0.8, 0.8)
                angle = impact_angle + spread
                speed = random.uniform(2.5, 6.5)
                vx = math.cos(angle) * speed + bigger.vx
                vy = math.sin(angle) * speed + bigger.vy
                color = random_color()
                particle_system.particles.append(Particle(smaller.x, smaller.y, vx, vy, color, mass=mass))
            loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)

        
        # Handle regular collisions (planets with planets)
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                if i not in bodies_to_remove and j not in bodies_to_remove:
                    b1, b2 = bodies[i], bodies[j]
                    if b1.body_type == "planet" and b2.body_type == "planet" and check_collision(b1, b2):
                        # Calculate relative velocity
                        rel_vx = b2.vx - b1.vx
                        rel_vy = b2.vy - b1.vy
                        rel_speed = math.hypot(rel_vx, rel_vy)
                        speed_threshold = 4.5  # You can tune this value

                        # Identify which is bigger
                        if b1.mass >= b2.mass:
                            bigger, smaller = b1, b2
                            bigger_idx, smaller_idx = i, j
                        else:
                            bigger, smaller = b2, b1
                            bigger_idx, smaller_idx = j, i

                        # CASE 1: Smaller hits bigger with HIGH speed
                        if smaller.vx**2 + smaller.vy**2 > bigger.vx**2 + bigger.vy**2 and rel_speed > speed_threshold:
                            particle_system.add_explosion(b1)
                            particle_system.add_explosion(b2)
                            bodies_to_remove.update([i, j])
                            loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)


                        # CASE 2: Smaller hits bigger with LOW speed
                        elif smaller.vx**2 + smaller.vy**2 < bigger.vx**2 + bigger.vy**2 and rel_speed <= speed_threshold:
                            bigger.consume(smaller)
                            bodies_to_remove.add(smaller_idx)
                            loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)

                        # CASE 3: Bigger hits smaller with HIGH speed
                        elif bigger.vx**2 + bigger.vy**2 > smaller.vx**2 + smaller.vy**2 and rel_speed > speed_threshold:
                            directional_explosion(bigger, smaller,round((bigger.mass+smaller.mass)/4),4)
                            bodies_to_remove.add(smaller_idx)
                            loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)

                        # CASE 4 (optional): fallback - explode both
                        else:
                            particle_system.add_explosion(b1)
                            particle_system.add_explosion(b2)
                            bodies_to_remove.update([i, j])
                            loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)
        
        for i, body in enumerate(bodies):
            # Check neutron star collisions
            for j in range(i + 1, len(bodies)):
                if i not in bodies_to_remove and j not in bodies_to_remove:
                    other = bodies[j]
                    if check_neutron_star_collision(body, other):
                        # Neutron stars collide
                        particles = body.collapse_to_neutron_star()
                        collapse_explosions.extend(particles)
                        bodies_to_remove.add(i)
                        bodies_to_remove.add(j)
                        loaded_Sounds = pSound(musicExplodeListPath, loaded_Sounds)


        # Remove consumed/exploded bodies
        bodies = [b for idx, b in enumerate(bodies) if idx not in bodies_to_remove]
        # Add collapse/explosion particles and new planets
        particle_system.particles.extend(collapse_explosions)
        bodies.extend(new_bodies)
        
        # Draw everything
        particle_system.draw(screen)
        for body in bodies:
            if not paused:
                body.update(bodies, particle_system,theory_options[selected_theory], time_lapse_multiplier)
            if show_trajectories:
                draw_predicted_trajectory(screen, body, bodies, years_per_frame)
            body.draw(screen)
        
        # Draw Inspect panel if object selected
        if inspect_mode and inspected_obj is not None:
            draw_inspect_panel(screen, inspected_obj)
        
        # Handle ongoing big bang events
        for bb in big_bang_events[:]:
            bb['timer'] += 1
            x, y = bb['x'], bb['y']
            # On first frame, remove any black hole at/near the big bang location and explode it
            if 1 <= bb['timer'] <= 110:
                bh_indices = [i for i, b in enumerate(bodies)
                            if b.body_type == "black_hole"]
                for i in reversed(bh_indices):
                    bh = bodies[i]
                    # Explode it into particles (similar to your supernova logic)
                    num_particles = min(100, int(bh.mass * 2))
                    for _ in range(num_particles):
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(3, 8)
                        vx = bh.vx + math.cos(angle) * speed
                        vy = bh.vy + math.sin(angle) * speed
                        color = (255, 100, 255)  # Bright magenta, feels cosmic
                        particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=bh.mass / num_particles))
                    bodies.pop(i)
            if bb['timer'] == 1:
                pygame.mixer.Sound("JustForFun/GravitySim/Attemp6/Assets/ExplosionSoundEffects/BB.mp3").play()
                bh_indices = [i for i, b in enumerate(bodies)
                              if b.body_type == "black_hole" and math.hypot(b.x - x, b.y - y) < 60]
                for i in reversed(bh_indices):
                    bh = bodies[i]
                    # Explode black hole into supernova-like particles
                    num_particles = min(100, int(bh.mass * 2))
                    for _ in range(num_particles):
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(8, 18)
                        vx = bh.vx + math.cos(angle) * speed
                        vy = bh.vy + math.sin(angle) * speed
                        color = (255, 100, 255)
                        particle_system.particles.append(Particle(bh.x, bh.y, vx, vy, color, mass=bh.mass/num_particles))
                    bodies.pop(i)
            # Phase 1: frame 20 - release 6 giant particles + 36 small planet waves
            if bb['timer'] == 20:
                for i in range(6):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(12, 20)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = (255, 200, 100)
                    particle_system.particles.append(Particle(x, y, vx, vy, color, mass=240))
                for i in range(36):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(12, 24)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = random_color()
                    mass = random.uniform(24, 54)
                    radius = max(3, int(mass))
                    bodies.append(Body(x, y, mass, radius, color, "planet"))
            # Phase 1.5: frame 30 - first white particle ring
            if bb['timer'] == 30:
                num_rings = 3
                base_particles = 120
                for ring in range(num_rings):
                    num_particles = base_particles + ring * 60
                    ring_radius = 60 + ring * 60
                    speed = 18 + ring * 8
                    for i in range(num_particles):
                        angle = 2 * math.pi * i / num_particles
                        vx = math.cos(angle) * speed
                        vy = math.sin(angle) * speed
                        px = x + math.cos(angle) * ring_radius
                        py = y + math.sin(angle) * ring_radius
                        color = (255, 255, 255)
                        particle_system.particles.append(Particle(px, py, vx, vy, color, mass=8))
            # Phase 2: frame 40 - release 18 medium planets and 9 stars
            if bb['timer'] == 40:
                for i in range(random.randrange(5,25)):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(9, 21)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = random_color()
                    mass = random.uniform(60, 120)
                    radius = max(5, int(mass/2))
                    bodies.append(Body(x, y, mass, radius, color, "planet"))
                for i in range(3):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(6, 15)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = (255, 255, 100)
                    mass = random.uniform(180, 360)
                    radius = max(8, int(mass ** 0.4))
                    bodies.append(Body(x, y, mass, radius, color, "star"))
            # Phase 2.5: frame 60 - second white particle ring (bigger)
            if bb['timer'] == 60:
                num_rings = 2
                base_particles = 180
                for ring in range(num_rings):
                    num_particles = base_particles + ring * 80
                    ring_radius = 200 + ring * 80
                    speed = 32 + ring * 10
                    for i in range(num_particles):
                        angle = 2 * math.pi * i / num_particles
                        vx = math.cos(angle) * speed
                        vy = math.sin(angle) * speed
                        px = x + math.cos(angle) * ring_radius
                        py = y + math.sin(angle) * ring_radius
                        color = (255, 255, 255)
                        particle_system.particles.append(Particle(px, py, vx, vy, color, mass=12))
            # Phase 3: frame 80 - supernova explosion (90 particles)
            if bb['timer'] == 80:
                for i in range(90):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(21, 42)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = (255, random.randint(100, 200), random.randint(0, 100))
                    particle_system.particles.append(Particle(x, y, vx, vy, color, mass=18))
            # Phase 4: frame 1-90 - keep generating particles (9 per frame)
            if 1 < bb['timer'] < 90:
                for _ in range(9):
                    angle = random.uniform(0, 2*math.pi)
                    speed = random.uniform(6, 30)
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    color = random_color()
                    particle_system.particles.append(Particle(x, y, vx, vy, color, mass=random.uniform(3, 12)))
            # Phase 5: frame 100 - final massive white particle ring
            if bb['timer'] == 100:
                num_particles = 360
                ring_radius = 400
                speed = 48
                for i in range(num_particles):
                    angle = 2 * math.pi * i / num_particles
                    vx = math.cos(angle) * speed
                    vy = math.sin(angle) * speed
                    px = x + math.cos(angle) * ring_radius
                    py = y + math.sin(angle) * ring_radius
                    color = (255, 255, 255)
                    particle_system.particles.append(Particle(px, py, vx, vy, color, mass=20))
            # End after 110 frames
            if bb['timer'] > 110:
                big_bang_events.remove(bb)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

def draw_predicted_trajectory(screen, body, bodies, years_per_frame, steps=100, step_size=1):
    """
    Draw a predicted trajectory for the body, with dots representing future positions.
    Each dot is spaced by step_size years. Dots are colored by how far in the future they are.
    """
    # Copy state
    x, y = body.x, body.y
    vx, vy = body.vx, body.vy
    mass = body.mass
    color = body.color
    points = []
    age = body.age
    for i in range(steps):
        fx, fy = 0, 0
        for other in bodies:
            if other is body:
                continue
            # Use Newtonian for prediction (faster)
            dx = other.x - x
            dy = other.y - y
            dist_sq = dx**2 + dy**2
            dist = math.sqrt(dist_sq)
            if dist < body.radius + getattr(other, 'radius', 0):
                continue
            force = G * mass * other.mass / (dist_sq + 1e-2)
            theta = math.atan2(dy, dx)
            fx += math.cos(theta) * force
            fy += math.sin(theta) * force
        # Update velocity and position
        vx += fx / mass / FPS
        vy += fy / mass / FPS
        x += vx
        y += vy
        # Wrap around screen edges
        if x < -body.radius:
            x = WIDTH + body.radius
        elif x > WIDTH + body.radius:
            x = -body.radius
        sim_height = HEIGHT - 200
        if y < -body.radius:
            y = sim_height + body.radius
        elif y > sim_height + body.radius:
            y = -body.radius
        # Add point every step_size years
        if i % int(step_size / years_per_frame) == 0:
            points.append((int(x), int(y), age + i * years_per_frame))
    # Draw trajectory line
    if len(points) > 1:
        pygame.draw.lines(screen, (180,220,255), False, [(px,py) for px,py,_ in points], 2)
    # Draw dots for each year, color fades with time
    for idx, (px, py, future_age) in enumerate(points):
        dot_color = (100, 255 - min(200, idx*2), 100 + min(155, idx*2))
        pygame.draw.circle(screen, dot_color, (px, py), 4)
        # Draw year label every 5th dot
        if idx % 5 == 0:
            font = pygame.font.Font(None, 18)
            year_label = f"{int(future_age)}"
            screen.blit(font.render(year_label, True, (255,255,180)), (px+6, py-6))


if __name__ == "__main__":
    main()