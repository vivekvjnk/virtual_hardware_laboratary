# Samples 
1. Question:
How many center aligned PWM timers are available in STM32F405?

Steps agent followed:
1. Agent used `browser tool` to download STM32F405 reference manual
2. Then used `cat on steroids` tool to gather information from the pdf file.

Answer: 
╭───────────────────────────────────────────────────────────── Message from Agent ─────────────────────────────────────────────────────────────╮
│                                                                                                                                              │
│ The STM32F405 has 6 timers that support center-aligned PWM: TIM1, TIM8, TIM2, TIM3, TIM4, and TIM5.                                          │
│                                                                                                                                              │
╰───────────────────────── Tokens: ↑ input 683.15K • cache hit 89.02% •  reasoning 4.29K • ↓ output 6.93K • $ 0.0854 ──────────────────────────╯


## Repeats
Repeated above experiment 4 times. Major bottleneck is browser use. 
Agent retries roughly 4-8 times before successfully downloading the reference manual.
First 2 cases, agent could download reference manual, but 3rd case agent failed to do so.

In first experiment, agent could understand timer 1 and 8 are capable of center aligned pwm. But failed to identify 2-5 timers. Final answer was also missing due to context overload.

In 2nd experiment agent finished the task with right answer.

In 3rd experiment, agent failed to download reference manual using browser tools. Then somehow got crashed and ended agent loop.

4th experiment: Agent finished task with right answer.

5th experiment: Agent finished task with right answer.

6th experiment: Browser operation failed.

7th experiment: Browser operation failed.

8th experiment: Agent finished task with right answer. 