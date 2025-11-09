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


// Smoke and ember color
void main() {
    vec2 uv = texCoords;
    uv -= 0.5;
    uv.x *= iResolution.x / iResolution.y;

    float time = iTime * 0.15;

    // Smoke movement using layered noise
    float smoke = 0.0;
    vec2 suv = uv * 2.0;
    for (int i = 0; i < 5; i++) {
        float f = float(i);
        smoke += (0.5 / f) * noise(suv * f * 0.8 + vec2(0.0, -time * f));
    }
    smoke = smoothstep(0.35, 0.75, smoke);

    // Glowing embers at bottom
    float emberMask = exp(-12.0 * length(uv - vec2(0.0, -0.3)));
    float flicker = 0.5 + 0.5 * sin(iTime * 6.0 + sin(iTime * 2.0));
    vec3 emberColor = vec3(1.0, 0.4, 0.05) * emberMask * (0.7 + 0.3 * flicker);

    // Smoke coloring (soft white/gray)
    vec3 smokeColor = mix(vec3(0.1, 0.1, 0.1), vec3(0.9), smoke * 0.9);

    // Blend smoke and embers
    vec3 color = mix(emberColor, smokeColor, smoke * 0.9);

    // Jar-like vignette
    float vignette = smoothstep(1.0, 0.6, length(uv));
    color *= vignette;

    fragColor = vec4(color, 1.0);
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