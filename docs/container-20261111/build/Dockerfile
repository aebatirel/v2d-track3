# V2D Challenge submission container. See CONTAINER_SUBMISSION.md.
# Team Imitation.Tech, Track 3 (pack 13h). Based on the kit's examples/container/Dockerfile; the additions are marked
# "Imitation.Tech".
#
# Build from a directory holding submission/ laid out as /submission will be:
#
#   submission/
#     submission.json   what each leaderboard submission was made from (schema in the guide)
#     run.sh            entry point (start from examples/container/run.sh)
#     code/             your repository, checked out at the submitted commit, .git included
#     kit/              the submission kit copy that packed and uploaded the submissions
#     verifier_kit/     the kit version that ships CONTAINER_SUBMISSION.md (for run.sh verify)
#     submitted/        the exact files uploaded to Kaggle, and their upload receipts
#     weights/          Tracks 2 and 3: one policy checkpoint per scored episode
#     outputs/          evaluator rollouts (Tracks 2 and 3) or final reconstructions (Track 1)
#
#   docker build -t TEAM-v2d-submission:FINAL -f Dockerfile .
#
# Start from the image you evaluated (Tracks 2 and 3) or reconstructed (Track 1) in, so the
# runtime that produced the leaderboard files is the one in the container.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Imitation.Tech: the base image's entry point (/opt/instance-tools/bin/entrypoint.sh) starts the Vast.ai instance
# services and ignores its arguments; clear it so `docker run IMAGE /submission/run.sh ...` runs the command.
ENTRYPOINT []

# Imitation.Tech: the FlashCHORD runtime (pinned evaluator commit, /opt/v2d) and the kit Python (/opt/kit-venv),
# installed as on our evaluation boxes; see install_runtime.sh. The build needs network access; a proxy CA, if any,
# is mounted as a build secret and is not kept in the image.
COPY install_runtime.sh /opt/install_runtime.sh
RUN --mount=type=secret,id=proxyca,required=false \
    if [ -f /run/secrets/proxyca ]; then \
      export SSL_CERT_FILE=/run/secrets/proxyca GIT_SSL_CAINFO=/run/secrets/proxyca PIP_CERT=/run/secrets/proxyca \
             REQUESTS_CA_BUNDLE=/run/secrets/proxyca; \
    fi; \
    PREFIX=/opt bash /opt/install_runtime.sh

# The verifier and entry point need git and the kit's Python requirements in the image.
# Keep file modes as committed: git would report a changed mode as a modified file.
# Make everything readable for reviewers who run the container as a non-root user. a+rX adds
# read access, and execute only on directories and already-executable files, so git still sees
# a clean checkout.
# Imitation.Tech: the kit's two steps (COPY submission /submission, then RUN chmod ...) in one layer: a chmod after
# COPY copies every file into a second layer (0.8 GB here). Same result: modes kept (cp -a), then the same chmod.
RUN --mount=type=bind,source=submission,target=/tmp/submission-src \
    cp -a /tmp/submission-src /submission && chmod 755 /submission/run.sh && chmod -R a+rX /submission
WORKDIR /submission
CMD ["/submission/run.sh", "verify"]
