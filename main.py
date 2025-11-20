import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import time, math, random


VERTEX_SHADER = """
#version 330
in vec2 position;
out vec2 texCoords;
void main() {
    texCoords = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
}
"""

FRAGMENT_SHADER = """
#version 330
in vec2 texCoords;
out vec4 fragColor;

uniform float iTime;
uniform vec2 iResolution;

// --- Noise Functions ---
float random(vec2 p) {
    return fract(sin(dot(p.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = random(i);
    float b = random(i + vec2(1.0, 0.0));
    float c = random(i + vec2(0.0, 1.0));
    float d = random(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 6; i++) {
        value += amplitude * noise(p);
        p *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

// --- SDF Functions ---
float sdRoundedBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b;
    return length(max(q, 0.0)) - r;
}

float sdJar(vec2 p) {
    float body = sdRoundedBox(p - vec2(0.0, -0.05), vec2(0.18, 0.22), 0.05);
    float neck = sdRoundedBox(p - vec2(0.0, 0.22), vec2(0.1, 0.04), 0.02);
    float rim = sdRoundedBox(p - vec2(0.0, 0.28), vec2(0.12, 0.02), 0.01);
    return min(min(body, neck), rim);
}

// --- Main Image ---
void main() {
    vec2 uv = (2.0 * texCoords - 1.0);
    uv.x *= iResolution.x / iResolution.y;
    vec2 original_uv = uv;
    uv -= vec2(0.8, -0.5); // Position jar in bottom right

    vec3 finalColor = vec3(0.0);
    float time = iTime * 0.25;

    // --- Jar ---
    float jarDist = sdJar(uv);
    float jarThickness = 0.01;

    // Glass appearance
    float glassAlpha = (1.0 - smoothstep(0.0, jarThickness, jarDist)) * 0.2;
    vec3 normal = normalize(vec3(dFdx(jarDist), dFdy(jarDist), -0.1));
    float highlight = pow(max(0.0, dot(reflect(vec3(0.0, 0.0, 1.0), normal), vec3(0.5, 0.5, 1.0))), 32.0);
    vec3 jarColor = vec3(0.7, 0.8, 1.0) * 0.5 + highlight * 0.5;

    // --- Ember ---
    vec2 emberPos = uv - vec2(0.0, -0.2);
    float emberShape = smoothstep(0.15, 0.0, length(emberPos));
    float emberGlow = smoothstep(0.4, 0.0, length(emberPos));
    float flicker = noise(vec2(iTime * 2.5)) * 0.6 + 0.4;
    float hotFlicker = pow(noise(vec2(iTime * 5.0, 10.0)), 15.0);
    vec3 emberColor = (vec3(1.0, 0.4, 0.1) * flicker + vec3(1.0, 0.8, 0.2) * hotFlicker) * emberShape;
    emberColor += vec3(0.8, 0.2, 0.0) * emberGlow * 0.4;

    // --- Smoke ---
    vec2 smoke_uv = uv;
    vec2 warp = vec2(fbm(smoke_uv * 2.0 + time * 0.5), fbm(smoke_uv * 2.0 + time * 0.5 + 5.0)) * 0.3;
    smoke_uv += warp;
    float smoke = fbm(smoke_uv * 3.0 + vec2(0.0, time * 0.8));
    smoke = smoothstep(0.4, 0.7, smoke);

    // Shape the smoke
    float inJar = 1.0 - smoothstep(-jarThickness, 0.0, jarDist);
    float jarOpening = smoothstep(0.25, 0.3, uv.y);
    float smokeMask = mix(inJar, 1.0, jarOpening);
    smoke *= (1.0 - smoothstep(0.0, 0.25, abs(uv.x))); // Confine horizontally
    smoke *= smoothstep(0.0, 0.4, uv.y + 0.2); // Make it rise
    smoke *= smokeMask;

    // Color the smoke
    vec3 smokeColor = vec3(0.9) * smoke; // White smoke

    // --- Composition ---
    finalColor = emberColor;
    finalColor = mix(finalColor, jarColor, glassAlpha);
    finalColor += smokeColor;

    float finalAlpha = max(glassAlpha, smoke) + emberGlow * 0.5;
    fragColor = vec4(finalColor, finalAlpha);
}
"""


def create_shader():
    return compileProgram(
        compileShader(VERTEX_SHADER, GL_VERTEX_SHADER),
        compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
    )

def main():
    pygame.init()
    info = pygame.display.Info()
    width, height = 1280, 720

    pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Glowing Embers and Smoke")

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.0, 0.0, 0.0, 1.0)

    shader = create_shader()
    glUseProgram(shader)

    vertices = np.array([
        -1.0, -1.0,
        1.0, -1.0,
        -1.0,  1.0,
        1.0,  1.0
    ], dtype=np.float32)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    position = glGetAttribLocation(shader, 'position')
    glVertexAttribPointer(position, 2, GL_FLOAT, GL_FALSE, 0, None)
    glEnableVertexAttribArray(position)

    iTime = glGetUniformLocation(shader, 'iTime')
    iResolution = glGetUniformLocation(shader, 'iResolution')

    clock = pygame.time.Clock()
    start = time.time()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False

        glClear(GL_COLOR_BUFFER_BIT)
        now = time.time() - start
        glUniform1f(iTime, now)
        glUniform2f(iResolution, width, height)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()