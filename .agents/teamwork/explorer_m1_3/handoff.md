# Handoff Report: Explorer M1.3 - Engine Diagnostics, Timing & Exit Codes

## 1. Observation

### 1.1 Highlight Style Default Defect in `PipelineConfig`
- **Location**: `core/engine.py`, lines 42 and 206–207; `core/parser/engine.py`, lines 60, 81.
- **Current Code**:
  - `core/engine.py:42`:
    ```python
    highlight_style: str = "kate"
    ```
  - `core/engine.py:206-207`:
    ```python
    if self.config.highlight_style:
        resolved_theme.highlight_style = self.config.highlight_style
    ```
  - `core/parser/engine.py:60`:
    ```python
    formatter = HtmlFormatter(nowrap=True, classprefix="tok-", style=style_name)
    ```
- **Observed Behavior**:
  - When `PipelineConfig` is instantiated directly via the Python API without explicitly passing `highlight_style=None`, `cfg.highlight_style` evaluates to `"kate"`.
  - In `ReportEngine.run()`, `"kate"` overrides the theme's resolved highlight style (`"one-dark"`).
  - Pygments 2.17+ raises:
    ```
    pygments.util.ClassNotFound: Could not find style module 'pygments.styles.kate'
    ```
  - In CLI invocation (`core/cli.py:67`, line 190), `--highlight-style` defaults to `None`, which is passed to `PipelineConfig`, bypassing the crash only in CLI mode.

### 1.2 Stage 1 Timer Misplacement & 0.00s Duration
- **Location**: `core/engine.py`, lines 114–165.
- **Current Code**:
  - Lines 114–158:
    ```python
    self.timer.start("total")
    input_file = self.config.input_file.resolve()
    validate_input_file(input_file)
    with open(input_file, "r", encoding="utf-8") as f:
        raw_content = f.read()
    temp_parser = MarkdownParser()
    cleaned_content, frontmatter = temp_parser.parse_frontmatter(raw_content)
    # [document title, language, i18n catalog resolution, target paths setup]
    target_html.parent.mkdir(parents=True, exist_ok=True)
    ```
  - Lines 163–164:
    ```python
    # STAGE 1: Document Ingestion & Validation
    self.timer.start("stage1")
    self.timer.stop("stage1")
    ```
- **Observed Behavior**:
  - The `stage1` timer is started and stopped on consecutive lines with an empty body.
  - Empirical measurement yields `2.38e-06` seconds (~2 microseconds).
  - All file existence checks, binary inspection, file reading, frontmatter parsing, metadata resolution, and directory creation occur before `stage1` timing begins.

### 1.3 Silent Exit Code 0 on PDF Compilation Failure
- **Location**: `core/engine.py`, lines 276–288, 338–364; `core/cli.py`, lines 205–218.
- **Current Code**:
  - `core/engine.py:363`:
    ```python
    Diagnostics.error("No suitable Chromium browser found for PDF export.")
    ```
  - `core/engine.py:276-288`:
    ```python
    if self.config.generate_pdf:
        self._compile_pdf(...)
        if target_html.is_file() and target_html != self.config.output_file:
            target_html.unlink(missing_ok=True)
    ...
    if not self.config.quiet:
        Diagnostics.success(
            f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)"
        )
    return self.config.output_file
    ```
  - `core/cli.py:205-218`:
    ```python
    try:
        engine = ReportEngine(cfg)
        out_file = engine.run()
    except Exception as e:
        Diagnostics.error(f"Compilation failed: {e}")
        sys.exit(1)
    ```
- **Observed Behavior**:
  - When `--pdf` is requested and no suitable headless browser or Bun/Node CDP script is found, `_compile_pdf()` logs an error to stderr but returns `None` without raising an exception.
  - `target_html` is deleted (`unlink`).
  - `run()` prints `[SUCCESS] Report generated: /path/to/missing.pdf`.
  - `core/cli.py` receives a normal return and terminates with exit code `0`.
  - The process exits cleanly despite the output PDF never being generated.

### 1.4 Missing Structured 5-Stage Timing Diagnostics in Verbose Mode
- **Location**: `core/engine.py`, lines 179–205, 248–252, 292–296.
- **Observed Behavior**:
  - In verbose mode (`-v`), only Stage 2 (Knowledge Pack sync) prints entity counts and execution time if entities are detected.
  - Stage 1, Stage 3, Stage 4, and Stage 5 times are never displayed.
  - No end-of-run structured breakdown of pipeline stage timing is printed.

---

## 2. Logic Chain

1. **Highlight Style Default Resolution**:
   - *Premise*: Document themes declare their own default `highlight_style` in `theme.yaml` (defaulting to `"one-dark"`). The pipeline config should only override this if the user explicitly requests an alternative.
   - *Observation*: `PipelineConfig.highlight_style` defaults to `"kate"`, an unsupported style in current Pygments that crashes any programmatic call.
   - *Deduction*: Setting `PipelineConfig.highlight_style = None` preserves declarative theme precedence while allowing CLI and programmatic overrides when non-None.

2. **Accurate Stage 1 Timing**:
   - *Premise*: Stage 1 encompasses Document Ingestion & Validation.
   - *Observation*: Ingestion and validation occur in lines 115–158, but `self.timer.start("stage1")` is called at line 163.
   - *Deduction*: Moving `self.timer.start("stage1")` to the entry point of `run()` (immediately following `self.timer.start("total")`) and stopping it before Stage 2 captures the true wall-clock time spent on validation, disk I/O, frontmatter parsing, and metadata resolution.

3. **Deterministic Failure Exit Codes**:
   - *Premise*: A failed artifact generation must fail fast, communicate the failure to automation pipelines, and return a non-zero exit code.
   - *Observation*: `_compile_pdf()` returns silently on total browser failure, leading to a misleading `[SUCCESS]` banner and exit code `0`.
   - *Deduction*: Raising `RuntimeError("PDF export failed: No suitable Chromium browser found or printer script returned an error.")` inside `_compile_pdf()` causes `engine.run()` to propagate the exception. `core/cli.py` catches `Exception` and exits with code `1`. Placing `target_html.unlink(...)` in a `finally` block guarantees that intermediate temporary HTML files are cleaned up even upon exception.

4. **Structured Verbose Diagnostic Metrics**:
   - *Premise*: Pipeline developers and forensic operators require stage-level timing diagnostics to identify bottlenecks across parsing, entity resolution, and bundling.
   - *Observation*: `PipelineTimer` already tracks durations for each stage (`stage1` through `stage5`), but verbose mode does not present this data.
   - *Deduction*: Adding `print_timing_breakdown()` to `ReportEngine` invoked when `self.config.verbose and not self.config.quiet` outputs a clear 5-stage timing table to `sys.stderr`. Exposing `get_stage_timings() -> Dict[str, float]` on `ReportEngine` enables programmatic and unit test verification.

---

## 3. Caveats

1. **Chromium Detection Precedence**:
   - `_compile_pdf()` prioritizes Bun/Node CDP printing (`viewer/scripts/print-pdf.mjs`) over direct Chromium binary execution. If Bun/Node is present but the script fails, it falls back to direct browser invocation before raising `RuntimeError`.
2. **Stderr vs Stdout Stream Separation**:
   - In accordance with `core/diagnostics.py`, all diagnostic messages, warnings, errors, and the timing breakdown table are emitted to `sys.stderr`. Generated report content and command results remain isolated from stderr streams.
3. **Loopback Networking in Air-Gapped Environments**:
   - The CDP printing bridge uses local loopback (`http://127.0.0.1:<port>`). In strict air-gap tests, loopback interfaces must remain accessible while WAN traffic is blocked.

---

## 4. Conclusion & Actionable Implementation Blueprint

The implementer agent should apply the following code changes:

### 4.1 Changes in `core/engine.py`

#### 4.1.1 Dataclass Default Update
**File**: `core/engine.py` (Line 42)
```python
# Before
highlight_style: str = "kate"

# After
highlight_style: Optional[str] = None
```

#### 4.1.2 Stage 1 Timer Repositioning & Logging
**File**: `core/engine.py` (Lines 113–165)
```python
# Before
    def run(self) -> Path:
        self.timer.start("total")
        input_file = self.config.input_file.resolve()
        validate_input_file(input_file)
        # [reading and metadata parsing]
        target_html.parent.mkdir(parents=True, exist_ok=True)

        # STAGE 1: Document Ingestion & Validation
        self.timer.start("stage1")
        self.timer.stop("stage1")

# After
    def run(self) -> Path:
        self.timer.start("total")
        # ------------------------------------------------------------------
        # STAGE 1: Document Ingestion & Validation
        # ------------------------------------------------------------------
        self.timer.start("stage1")
        input_file = self.config.input_file.resolve()
        validate_input_file(input_file)
        # [reading and metadata parsing]
        target_html.parent.mkdir(parents=True, exist_ok=True)
        self.timer.stop("stage1")

        if not self.config.quiet and self.config.verbose:
            Diagnostics.info(
                f"Stage 1: Document Ingestion & Validation ({self.timer.get('stage1'):.2f}s)"
            )
```

#### 4.1.3 Stages 3 & 4 Verbose Per-Stage Output
**File**: `core/engine.py` (Lines 201–205 and 245–252)
```python
# Stage 3 After:
        if not self.config.quiet:
            chain_str = " -> ".join(resolved_theme.inheritance_chain)
            time_suffix = f" ({self.timer.get('stage3'):.2f}s)" if self.config.verbose else ""
            Diagnostics.info(f"Stage 3: Theme resolved: {resolved_theme.name} [{chain_str}]{time_suffix}")

# Stage 4 After:
        if not self.config.quiet:
            if self.config.verbose:
                Diagnostics.info(
                    f"Stage 4: Markdown AST & Transforms compiled ({self.timer.get('stage4'):.2f}s)"
                )
            elif self.metrics.diagrams_rendered > 0:
                Diagnostics.info(
                    f"Stage 4: Processed {self.metrics.diagrams_rendered} diagram(s)"
                )
```

#### 4.1.4 Stage 5 Output Bundling, PDF Cleanup, and Diagnostics Summary
**File**: `core/engine.py` (Lines 274–297)
```python
# Before
        if self.config.generate_pdf:
            self._compile_pdf(
                target_html,
                self.config.output_file,
                theme=resolved_theme,
                catalog=catalog,
                title=doc_title,
                frontmatter=frontmatter,
                bundler=bundler
            )
            if target_html.is_file() and target_html != self.config.output_file:
                target_html.unlink(missing_ok=True)

        self.timer.stop("stage5")
        total_time = self.timer.stop("total")

        if not self.config.quiet:
            Diagnostics.success(
                f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)"
            )

        return self.config.output_file

# After
        if self.config.generate_pdf:
            try:
                self._compile_pdf(
                    target_html,
                    self.config.output_file,
                    theme=resolved_theme,
                    catalog=catalog,
                    title=doc_title,
                    frontmatter=frontmatter,
                    bundler=bundler
                )
            finally:
                if target_html.is_file() and target_html != self.config.output_file:
                    target_html.unlink(missing_ok=True)

        self.timer.stop("stage5")
        if not self.config.quiet and self.config.verbose:
            Diagnostics.info(
                f"Stage 5: Output Bundling & Export completed ({self.timer.get('stage5'):.2f}s)"
            )
        total_time = self.timer.stop("total")

        if not self.config.quiet:
            if self.config.verbose:
                self.print_timing_breakdown(total_time)
            Diagnostics.success(
                f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)"
            )

        return self.config.output_file
```

#### 4.1.5 Public Diagnostics Helper Methods
**File**: `core/engine.py` (Appended to `ReportEngine`)
```python
    def get_stage_timings(self) -> Dict[str, float]:
        """Returns durations for all 5 pipeline stages and total elapsed time."""
        return {
            "stage1": self.timer.get("stage1"),
            "stage2": self.timer.get("stage2"),
            "stage3": self.timer.get("stage3"),
            "stage4": self.timer.get("stage4"),
            "stage5": self.timer.get("stage5"),
            "total": self.timer.get("total"),
        }

    def print_timing_breakdown(self, total_time: float) -> None:
        """Prints a structured 5-stage timing breakdown to stderr."""
        s1 = self.timer.get("stage1")
        s2 = self.timer.get("stage2")
        s3 = self.timer.get("stage3")
        s4 = self.timer.get("stage4")
        s5 = self.timer.get("stage5")
        print("", file=sys.stderr)
        print(f"{Colors.BOLD}Pipeline Timing Breakdown:{Colors.RESET}", file=sys.stderr)
        print(f"  • Stage 1 (Validation & Ingestion):     {s1:6.2f}s", file=sys.stderr)
        print(f"  • Stage 2 (Knowledge Pack Sync):        {s2:6.2f}s", file=sys.stderr)
        print(f"  • Stage 3 (Theme Resolution):           {s3:6.2f}s", file=sys.stderr)
        print(f"  • Stage 4 (Markdown AST & Transforms):  {s4:6.2f}s", file=sys.stderr)
        print(f"  • Stage 5 (Output Bundling & Export):   {s5:6.2f}s", file=sys.stderr)
        print(f"  • Total Compilation Time:               {total_time:6.2f}s", file=sys.stderr)
        print("", file=sys.stderr)
```

#### 4.1.6 Exception Raising in `_compile_pdf()`
**File**: `core/engine.py` (Lines 360–364)
```python
# Before
            if res.returncode == 0 and dst_pdf.is_file() and dst_pdf.stat().st_size > 0:
                return
            Diagnostics.warn(f"Browser PDF failed: {res.stderr}")

        Diagnostics.error("No suitable Chromium browser found for PDF export.")

# After
            if res.returncode == 0 and dst_pdf.is_file() and dst_pdf.stat().st_size > 0:
                return
            Diagnostics.warn(f"Browser PDF failed: {res.stderr}")

        if dst_pdf.is_file() and dst_pdf.stat().st_size == 0:
            dst_pdf.unlink(missing_ok=True)

        Diagnostics.error("No suitable Chromium browser found for PDF export.")
        raise RuntimeError(
            "PDF export failed: No suitable Chromium browser found or printer script returned an error."
        )
```

### 4.2 Machine-Applicable Artifacts Prepared
- Patch file: `.agents/teamwork/explorer_m1_3/engine_diagnostics.patch`
- Unit test suite: `.agents/teamwork/explorer_m1_3/proposed_test_engine_diagnostics.py`

---

## 5. Verification Method

To verify these changes:

1. **Verify Baseline Test Suite (0 Regressions)**:
   ```bash
   uv run pytest
   ```
   *Expected*: All 87 unit tests pass.

2. **Verify `PipelineConfig` Default Highlight Style**:
   ```bash
   uv run python -c "
   from pathlib import Path
   from core.engine import ReportEngine, PipelineConfig
   src = Path('/tmp/test_pyg.md')
   src.write_text('# Test\n\`\`\`python\nprint(1)\n\`\`\`\n', encoding='utf-8')
   cfg = PipelineConfig(input_file=src, output_file=Path('/tmp/test_pyg.html'))
   assert cfg.highlight_style is None
   ReportEngine(cfg).run()
   print('Verification passed: Programmatic compilation succeeded without kate crash')
   "
   ```

3. **Verify Stage 1 Timer Metric**:
   ```bash
   uv run python -c "
   from pathlib import Path
   from core.engine import ReportEngine, PipelineConfig
   src = Path('/tmp/test_s1.md')
   src.write_text('# Stage 1 Test\nContent\n', encoding='utf-8')
   cfg = PipelineConfig(input_file=src, output_file=Path('/tmp/test_s1.html'), quiet=True)
   engine = ReportEngine(cfg)
   engine.run()
   timings = engine.get_stage_timings()
   assert timings['stage1'] > 0.0, f'Expected stage1 > 0, got {timings[\"stage1\"]}'
   print('Stage 1 duration:', timings['stage1'])
   "
   ```

4. **Verify PDF Failure Exit Code 1**:
   ```bash
   uv run python -c "
   import subprocess, sys
   res = subprocess.run(
       [sys.executable, '-m', 'core.cli', '/tmp/test_s1.md', '-o', '/tmp/fail.pdf', '--pdf'],
       env={'PATH': '/nonexistent', 'HOME': '/tmp'},
       capture_output=True,
       text=True
   )
   assert res.returncode == 1, f'Expected exit code 1, got {res.returncode}'
   print('Verification passed: CLI exited with code 1 on PDF failure')
   "
   ```

5. **Verify Verbose 5-Stage Timing Diagnostics**:
   ```bash
   uv run python -c "
   import subprocess, sys
   res = subprocess.run(
       [sys.executable, '-m', 'core.cli', '/tmp/test_s1.md', '-o', '/tmp/verbose.html', '-v'],
       capture_output=True,
       text=True
   )
   assert 'Pipeline Timing Breakdown:' in res.stderr
   assert 'Stage 1 (Validation & Ingestion):' in res.stderr
   assert 'Stage 5 (Output Bundling & Export):' in res.stderr
   print('Verification passed: Verbose mode prints complete 5-stage timing breakdown')
   "
   ```

6. **Execute Diagnostic Unit Tests**:
   Deploy `proposed_test_engine_diagnostics.py` to `tests/test_engine_diagnostics.py` and run:
   ```bash
   uv run pytest tests/test_engine_diagnostics.py
   ```
   *Expected*: All 7 diagnostic tests pass.
