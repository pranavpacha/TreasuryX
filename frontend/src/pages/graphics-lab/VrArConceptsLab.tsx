import { Badge, Panel } from "../../components/Common";

export default function VrArConceptsLab() {
  return (
    <div>
      <Panel title="VR / AR / XR Concepts — CS4104 Modules 4 & 5">
        <Badge kind="warn">CONCEPTUAL ONLY — NO VR/AR HARDWARE USED</Badge>
        <p style={{ fontSize: 12, color: "var(--text-mid)", marginTop: 10 }}>
          Per the project's own scope (it must run on a normal laptop, no VR headset or AR device required), this
          page documents the syllabus's VR/AR/XR concepts rather than pretending to implement them. Nothing here is
          rendered in stereo, tracked with real sensors, or run on an HMD.
        </p>
      </Panel>

      <div className="grid grid-2">
        <Panel title="VR System Architecture & Hardware">
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>HMD (Head-Mounted Display)</td><td style={{ textAlign: "left" }}>Stereo display + lenses per eye, creating depth via binocular disparity</td></tr>
              <tr><td style={{ textAlign: "left" }}>Controllers / sensors</td><td style={{ textAlign: "left" }}>Hand tracking, buttons, haptics for interaction in the virtual environment</td></tr>
              <tr><td style={{ textAlign: "left" }}>3DOF</td><td style={{ textAlign: "left" }}>Rotational tracking only (pitch/yaw/roll) — e.g. a fixed-position headset</td></tr>
              <tr><td style={{ textAlign: "left" }}>6DOF</td><td style={{ textAlign: "left" }}>Rotational + positional tracking — the user can physically move in space</td></tr>
              <tr><td style={{ textAlign: "left" }}>Inside-out tracking</td><td style={{ textAlign: "left" }}>Cameras on the headset track the environment (e.g. Meta Quest)</td></tr>
              <tr><td style={{ textAlign: "left" }}>Outside-in tracking</td><td style={{ textAlign: "left" }}>External base stations track the headset (e.g. early HTC Vive)</td></tr>
            </tbody>
          </table>
        </Panel>
        <Panel title="Human Factors in VR">
          <table className="data-table">
            <tbody>
              <tr><td style={{ textAlign: "left" }}>Field of view (FOV)</td><td style={{ textAlign: "left" }}>Wider FOV increases immersion but raises rendering cost and can increase distortion at the edges</td></tr>
              <tr><td style={{ textAlign: "left" }}>Latency</td><td style={{ textAlign: "left" }}>Delay between head movement and display update — the single biggest driver of motion sickness</td></tr>
              <tr><td style={{ textAlign: "left" }}>Motion sickness</td><td style={{ textAlign: "left" }}>Caused by a mismatch between visual motion cues and the vestibular (inner-ear) sense of motion</td></tr>
              <tr><td style={{ textAlign: "left" }}>Ergonomics</td><td style={{ textAlign: "left" }}>Headset weight/balance and session duration affect user comfort and adoption</td></tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel title="Extended Reality (XR) Concepts">
        <table className="data-table">
          <tbody>
            <tr><td style={{ textAlign: "left" }}>Marker-based AR</td><td style={{ textAlign: "left" }}>Overlays content by detecting a known visual marker (e.g. a QR-like fiducial) in the camera feed</td></tr>
            <tr><td style={{ textAlign: "left" }}>Markerless AR</td><td style={{ textAlign: "left" }}>Uses SLAM (simultaneous localization and mapping) to place content relative to detected real-world surfaces/features without a predefined marker</td></tr>
            <tr><td style={{ textAlign: "left" }}>Spatial computing</td><td style={{ textAlign: "left" }}>Blending digital content with a real-time understanding of 3D physical space</td></tr>
          </tbody>
        </table>
        <p style={{ fontSize: 11, color: "var(--text-mid)", marginTop: 10 }}>
          A hypothetical Treasury-relevant XR application: a dealer wearing an AR headset could see a live risk
          heatmap overlaid on a physical trading-floor display -- illustrative only, not built here.
        </p>
      </Panel>

      <Panel title="What IS implemented instead, covering the same underlying graphics concepts">
        <p style={{ fontSize: 11, color: "var(--text-mid)" }}>
          The 3D Graphics Lab's camera/projection, transformation-matrix, lighting/shading, and depth-buffer
          material covers the same mathematical foundations (view/projection matrices, perspective, illumination
          models) that a VR renderer also relies on -- just delivered through a standard laptop display via WebGL
          rather than a stereo HMD.
        </p>
      </Panel>
    </div>
  );
}
