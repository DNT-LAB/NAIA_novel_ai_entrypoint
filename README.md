이 코드는 바이브 코딩을 기반으로 자신만의 NovelAI 이미지 생성 도구를 만들고자 하는 사용자들을 위한 All-in-One API Docs입니다. AI 코딩 어시스턴트에게 `naia.py`를 읽게 하면, API 스펙부터 사용 예시까지 모든 정보를 즉시 파악하고 개발을 시작할 수 있습니다.

## How to Use

1. **naia.py 다운로드** — 이 저장소에서 `naia.py` 파일 하나만 받으면 됩니다.

2. **CLI 도구와 함께 사용** — 아래 중 하나를 설치하세요:
   - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`)
   - [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`)
   - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`npm install -g @anthropic-ai/gemini-cli`)

3. **CLI 도구에게 시키기** — `naia.py`가 있는 폴더에서 claude, codex, gemini 등을 실행 후:
   ```
   naia.py를 읽고 이미지 생성 테스트를 해줘. 토큰: pst-여기에토큰붙여넣기
   ```

API 토큰은 NovelAI 웹사이트 → Settings → Account → "Get Persistent API Token"에서 발급받을 수 있습니다.
