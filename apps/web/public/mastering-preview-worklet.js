/**
 * Low-latency mastering approximation for interactive browser preview.
 *
 * The production renderer remains authoritative. This processor provides audible,
 * parameter-smoothed gain staging, saturation, clipping, lookahead limiting, and
 * delivery-depth audition without backend work.
 */
class MasteringPreviewProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [
      { name: "inputGainDb", defaultValue: 0, minValue: -12, maxValue: 12, automationRate: "k-rate" },
      { name: "saturation", defaultValue: 0, minValue: 0, maxValue: 1, automationRate: "k-rate" },
      { name: "clipperDriveDb", defaultValue: 0, minValue: 0, maxValue: 12, automationRate: "k-rate" },
      { name: "ceilingDbfs", defaultValue: -1, minValue: -6, maxValue: -.1, automationRate: "k-rate" },
      { name: "lookaheadMs", defaultValue: 3, minValue: 0, maxValue: 10, automationRate: "k-rate" },
      { name: "releaseMs", defaultValue: 80, minValue: 10, maxValue: 500, automationRate: "k-rate" },
      { name: "bitDepth", defaultValue: 24, minValue: 16, maxValue: 32, automationRate: "k-rate" },
      { name: "bypass", defaultValue: 0, minValue: 0, maxValue: 1, automationRate: "k-rate" },
    ];
  }

  constructor() {
    super();
    this.delay = [];
    this.writeIndex = 0;
    this.envelope = 1;
    this.randomState = 0x6d2b79f5;
  }

  random() {
    this.randomState = (Math.imul(this.randomState, 1664525) + 1013904223) >>> 0;
    return this.randomState / 4294967296;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (!input.length || !output.length) return true;
    const value = (name) => parameters[name][0];
    const bypass = value("bypass") >= .5;
    const frameCount = output[0].length;
    const lookahead = bypass ? 0 : Math.round(value("lookaheadMs") * sampleRate / 1000);
    const ringLength = Math.max(1, Math.round(.010 * sampleRate) + frameCount + 1);
    while (this.delay.length < output.length) this.delay.push(new Float32Array(ringLength));
    const inputGain = bypass ? 1 : 10 ** (value("inputGainDb") / 20);
    const saturation = bypass ? 0 : value("saturation");
    const drive = bypass ? 1 : 10 ** (value("clipperDriveDb") / 20);
    const ceiling = 10 ** ((bypass ? 0 : value("ceilingDbfs")) / 20);
    const release = Math.exp(-1 / (Math.max(10, value("releaseMs")) * sampleRate / 1000));
    const bits = bypass ? 32 : Math.round(value("bitDepth"));
    const quantizer = bits >= 32 ? 0 : 2 ** (bits - 1) - 1;

    for (let frame = 0; frame < frameCount; frame += 1) {
      let linkedPeak = 0;
      for (let channel = 0; channel < output.length; channel += 1) {
        const dry = input[channel]?.[frame] ?? input[0]?.[frame] ?? 0;
        let wet = dry * inputGain;
        if (!bypass && saturation > 0) {
          // Mastering saturation stays deliberately subtle to protect bass transients.
          const saturationDrive = 1 + saturation * .75;
          const shaped = Math.tanh(wet * saturationDrive) / Math.tanh(saturationDrive);
          wet = wet * (1 - saturation * .14) + shaped * saturation * .14;
        }
        if (!bypass && drive > 1) {
          const shaped = Math.tanh(wet * drive) / drive;
          const clipMix = Math.min(.7, value("clipperDriveDb") / 12);
          wet = wet * (1 - clipMix) + shaped * clipMix;
        }
        this.delay[channel][this.writeIndex] = wet;
        linkedPeak = Math.max(linkedPeak, Math.abs(wet));
      }
      const target = Math.min(1, ceiling / Math.max(linkedPeak, 1e-12));
      this.envelope = Math.min(target, 1 - (1 - this.envelope) * release);
      const readIndex = (this.writeIndex - lookahead + ringLength) % ringLength;
      for (let channel = 0; channel < output.length; channel += 1) {
        let sample = this.delay[channel][readIndex] * this.envelope;
        if (quantizer) {
          const tpdf = (this.random() - this.random()) / quantizer;
          sample = Math.round((sample + tpdf) * quantizer) / quantizer;
        }
        output[channel][frame] = Math.max(-ceiling, Math.min(ceiling, sample));
      }
      this.writeIndex = (this.writeIndex + 1) % ringLength;
    }
    return true;
  }
}

registerProcessor("mastering-preview", MasteringPreviewProcessor);
