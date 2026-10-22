# Draft: questions to the V2D organisers (2026-10-22)

For the owner to send (v2d_challenge@nvidia.com or the official Discord). Not sent by the agent. Note 19 §4 has the
longer collision-geometry wording, with the measurements behind it.

---

**Subject:** Track 3: own reconstructed meshes, collision geometry, the spoon

Hello V2D team,

We are a Track 3 team using our own reconstructed object meshes (FAQ: "participants should submit their own
reconstructed meshes"). Before our final runs we would like to confirm four points.

1. **Collision geometry separate from the submitted mesh.** May the simulator asset's `<collision>` geometry differ
   from the visual mesh we submit for scoring? An example is the same reconstruction made watertight, split into
   several `<collision>` pieces, or given a flat support patch where the object was seen resting on the table. The
   evaluator, the CoACD call and all physics parameters would stay unchanged. The same question applies to
   `<inertial>` (the provided URDFs call 0.3 kg a placeholder).

2. **Completing regions the cameras never see.** Undersides hidden by the table and the inside of narrow slots are
   never observed. May we complete them with rules applied automatically and identically to every episode, using
   only our own observations? Examples:
   - a flat base at the table plane where the object is seen resting;
   - removing volume that another tracked object occupies at the same time;
   - simple shape families fitted to our depth, such as a slab for a board or a surface of revolution for a cup.

   Does that still count as our own reconstruction? Would a pretrained image-to-3D model run on the eval video, used
   only for never-observed regions, also count?

3. **How we bootstrap the meshes.** To build our first meshes from the public videos, we tracked the objects with
   FoundationPose using the public scans as templates. Our final pipeline will instead track each eval video with our
   own meshes and then re-fuse each eval episode's submitted mesh from that episode's own video, along those tracks.
   Is that acceptable, or must the whole chain avoid the public scans, including that first tracking pass on public
   episodes?

4. **The wooden spoon** (no public asset). We start tracking from a parametric spoon model built from our own
   measurements in the videos, then fuse the submitted mesh from the eval videos along our tracks. Is that acceptable?

Optional, if easy to answer: does validation run the kit runner at world_count 1, and on which platform (Linux x86_64
or aarch64)? CoACD gives slightly different hulls across platforms.

Thank you,
<name / team>
