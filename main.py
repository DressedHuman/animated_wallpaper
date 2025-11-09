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

// Simple 2D noise function
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
               mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

// SDF for a circle
float sdCircle(vec2 p, float r) {
    return length(p) - r;
}

// SDF for a box
float sdBox(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

// Function to create the jar shape using SDF
float sdJar(vec2 p) {
    float body = sdBox(p - vec2(0.0, -0.1), vec2(0.2, 0.25));
    float neck = sdBox(p - vec2(0.0, 0.2), vec2(0.1, 0.05));
    float rim = sdBox(p - vec2(0.0, 0.28), vec2(0.15, 0.02));

    float jar = min(body, neck);
    jar = min(jar, rim);

    return jar;
}

void main() {
    vec2 uv = (2.0 * texCoords - 1.0) * vec2(iResolution.x / iResolution.y, 1.0);

    // Move coordinate system to bottom right
    uv -= vec2(0.6, -0.6);

    // Jar color and transparency
    float jarSDF = sdJar(uv);
    vec3 jarColor = vec3(0.8, 0.9, 1.0); // Light blue tint for glass
    float jarAlpha = (1.0 - smoothstep(0.0, 0.01, jarSDF)) * 0.2;
    float jarRim = smoothstep(0.0, 0.01, abs(sdJar(uv)) - 0.01);
    jarColor = mix(jarColor, vec3(1.0), 1.0 - jarRim) * 0.5;

    // Ember
    float emberMask = smoothstep(0.2, 0.0, length(uv - vec2(0.0, -0.2)));
    float flicker = noise(vec2(iTime * 2.0, 0.0)) * 0.5 + 0.5;
    vec3 emberColor = vec3(1.0, 0.3, 0.0) * emberMask * flicker;

    // Smoke
    float time = iTime * 0.2;
    float smoke = 0.0;
    vec2 suv = uv * 3.0;
    for (int i = 1; i < 6; i++) {
        float f = float(i);
        smoke += (1.0 / f) * noise(suv * f * 0.5 + vec2(0.0, -time));
    }
    smoke = smoothstep(0.4, 0.7, smoke);
    smoke *= smoothstep(0.0, 0.3, uv.y + 0.2); // Smoke rises

    vec3 smokeColor = vec3(0.8) * smoke;

    // Combine everything
    vec3 color = emberColor + smokeColor;
    color = mix(color, jarColor, jarAlpha);

    // Final color with transparency
    float finalAlpha = max(smoke * 0.5, jarAlpha);
    fragColor = vec4(color, finalAlpha);
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