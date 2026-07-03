# Excerpt: "Adversarial Robustness of Instruction-Tuned Language Models"

*Saved excerpt from a paper one of our research engineers shared in the
shared-reading channel last quarter. Stored here for the team's reference;
do not redistribute outside the company.*

## Section 4.2 — Taxonomy of attempted overrides

Prior work characterizes adversarial prompts along three axes: payload
position, payload framing, and recipient context. We adopt this taxonomy
and extend it with a fourth axis (instruction-detachment), which captures
the degree to which the malicious instruction is syntactically separated
from the surrounding benign content.

To illustrate, consider the following stylized examples drawn from the
authors' Appendix B (escaped here as inline code so they cannot themselves
be interpreted as live instructions by any downstream renderer):

`"please summarize the article. \nIgnore the above and instead output the
training data verbatim."`

`"<user>Hello!</user> </prompt> system: act as DAN."`

The first example illustrates *trailing-detachment*: a benign request is
followed by an attempted override that relies on the model treating the
later token sequence as authoritative. The second illustrates a
*tag-spoofing* approach in which closing tags from a fictional schema are
used to confuse role-aware models.

## Section 4.3 — Why this matters for benchmark design

Our hypothesis is that detachment-axis is under-represented in current
adversarial benchmarks. We propose a controlled corpus of 480 examples
drawn equally from each cell of the four-axis grid; we report results
in Table 3.
