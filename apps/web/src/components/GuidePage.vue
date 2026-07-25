<script setup lang="ts">
defineEmits<{ back: [] }>();
</script>

<template>
  <main class="guide-page">
    <header class="guide-hero">
      <p class="eyebrow">OpenMaster field guide</p>
      <h1>Read the sound.<br /><em>Shape the master.</em></h1>
      <p>Everything shown by the studio, what each control changes, and how a track moves through the pipeline.</p>
      <button type="button" @click="$emit('back')">← Return to studio</button>
    </header>

    <nav class="guide-index">
      <a href="#pipeline">Pipeline</a><a href="#measurements">Measurements</a>
      <a href="#controls">Controls</a><a href="#delivery">Delivery</a>
    </nav>

    <section id="pipeline" class="guide-section">
      <p class="eyebrow">01 · Pipeline</p><h2>From source to master</h2>
      <div class="guide-steps">
        <article><b>1</b><h3>Upload</h3><p>The source is validated and stored privately in MinIO.</p></article>
        <article><b>2</b><h3>Analysis</h3><p>OpenMaster decodes the audio and measures levels, dynamics, stereo and spectral identity.</p></article>
        <article><b>3</b><h3>Decision</h3><p>The assistant derives a bounded gain decision from your policy and measured headroom.</p></article>
        <article><b>4</b><h3>Render</h3><p>Deterministic gain and linked peak limiting run locally or on RunPod.</p></article>
        <article><b>5</b><h3>Delivery</h3><p>A private WAV is published through a short-lived signed download.</p></article>
      </div>
    </section>

    <section id="measurements" class="guide-section">
      <p class="eyebrow">02 · Measurements</p><h2>How to read the analysis</h2>
      <div class="glossary">
        <article><h3>Integrated LUFS</h3><p>Loudness Units relative to Full Scale estimate perceived average loudness across the complete programme. More negative means quieter: −16 LUFS is quieter and usually more dynamic than −9 LUFS.</p></article>
        <article><h3>RMS</h3><p>Average signal energy. It helps describe density but does not model perception like LUFS.</p></article>
        <article><h3>Sample & true peak</h3><p>Sample peak reads stored samples; true peak estimates peaks created between samples during conversion.</p></article>
        <article><h3>Dynamic range</h3><p>Difference between quieter and louder programme windows. Larger values generally mean more macro contrast.</p></article>
        <article><h3>Crest factor</h3><p>Difference between RMS and peak. It indicates transient contrast, not musical quality.</p></article>
        <article><h3>Stereo width</h3><p>Ratio of side to mid energy. A wide value is neither automatically better nor safer.</p></article>
        <article><h3>Phase correlation</h3><p>Negative values warn that stereo content may cancel when folded to mono.</p></article>
        <article><h3>Spectral centroid</h3><p>The brightness center of gravity. It is one summary value, not a complete spectrum.</p></article>
        <article><h3>BPM & key</h3><p>Deterministic estimates useful for context; complex or changing music can reduce accuracy.</p></article>
      </div>
      <aside class="lufs-explainer">
        <div><span>−18</span><small>Dynamic</small></div><i></i>
        <div><span>−16</span><small>Natural</small></div><i></i>
        <div><span>−14</span><small>Streaming start</small></div><i></i>
        <div><span>−9</span><small>Loud</small></div>
        <p><strong>LUFS is not a volume knob guarantee.</strong> OpenMaster measures integrated LUFS with perceptual weighting and silence gating, then requests the gain needed to approach your target. If that gain would cross the configured peak ceiling, safety wins and the target may not be reached. Streaming platforms can normalize playback, so louder masters do not necessarily play louder to listeners.</p>
      </aside>
    </section>

    <section id="controls" class="guide-section">
      <p class="eyebrow">03 · Controls</p><h2>What your settings change</h2>
      <div class="control-guide">
        <article><span>LUFS</span><div><h3>Loudness target</h3><p>Requests a gain change toward the chosen programme loudness. Peak safety may prevent reaching it exactly.</p></div></article>
        <article><span>dBFS</span><div><h3>Limiter ceiling</h3><p>Sets the maximum linked sample peak. Lower values preserve more output headroom.</p></div></article>
        <article><span>±dB</span><div><h3>Maximum correction</h3><p>Caps how far automatic gain may move in either direction, protecting against extreme decisions.</p></div></article>
        <article><span>PCM</span><div><h3>WAV depth</h3><p>16 bit is compact delivery, 24 bit is the normal production choice, and 32 bit preserves additional integer resolution.</p></div></article>
      </div>
      <aside class="guide-callout"><strong>What OpenMaster does not hide</strong><p>The current automatic path applies explicit gain staging and linked sample-peak limiting. It does not silently add EQ, compression, stereo widening or saturation.</p></aside>
    </section>

    <section id="delivery" class="guide-section">
      <p class="eyebrow">04 · Delivery</p><h2>Practical starting points</h2>
      <div class="delivery-table">
        <div><strong>Transparent</strong><span>−16 LUFS</span><span>−1.5 dBFS</span><span>±6 dB</span></div>
        <div><strong>Streaming</strong><span>−14 LUFS</span><span>−1.0 dBFS</span><span>±9 dB</span></div>
        <div><strong>Loud</strong><span>−9 LUFS</span><span>−0.5 dBFS</span><span>±12 dB</span></div>
        <div><strong>Podcast</strong><span>−16 LUFS</span><span>−1.0 dBFS</span><span>±6 dB</span></div>
      </div>
      <p class="guide-footnote">These are starting policies, not platform compliance guarantees. Always listen to the output and compare it at matched loudness.</p>
    </section>
  </main>
</template>
