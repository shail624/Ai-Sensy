# Hermetic browser-test runner. The browser build and operating-system dependencies are locked
# together so a provider can execute the same journey without pre-installing Chromium.
FROM mcr.microsoft.com/playwright:v1.61.1-noble@sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48

WORKDIR /tests
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json playwright.config.ts ./
COPY tests ./tests
RUN npm run typecheck

USER pwuser
ENTRYPOINT ["npx", "playwright", "test", "--config=playwright.config.ts"]
