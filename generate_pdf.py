import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Adds running headers and total page count footers."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#666666"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 20, page_text)
        self.drawString(36, 20, "LangGraph Engineering & Architecture — Study Notes")
        self.setStrokeColor(colors.HexColor("#E0E0E6"))
        self.setLineWidth(0.5)
        self.line(36, 30, letter[0] - 36, 30)
        self.restoreState()


pdf_filename = "LangGraph_Engineering_Study_Notes.pdf"
doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    leftMargin=36,
    rightMargin=36,
    topMargin=36,
    bottomMargin=38
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=17,
    leading=21,
    textColor=colors.HexColor('#1E1B4B')
)

subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=9,
    leading=12,
    textColor=colors.HexColor('#555566')
)

h1_style = ParagraphStyle(
    'SectionHeading',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=11,
    leading=14,
    textColor=colors.HexColor('#1E1B4B'),
    spaceBefore=9,
    spaceAfter=4,
    keepWithNext=True
)

h2_style = ParagraphStyle(
    'SubSectionHeading',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=9.5,
    leading=12.5,
    textColor=colors.HexColor('#312E81'),
    spaceBefore=7,
    spaceAfter=3,
    keepWithNext=True
)

body_style = ParagraphStyle(
    'BodyDark',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=8.2,
    leading=11.5,
    textColor=colors.HexColor('#222222')
)

bold_body_style = ParagraphStyle(
    'BoldBody',
    parent=body_style,
    fontName='Helvetica-Bold'
)

q_style = ParagraphStyle(
    'ActiveRecallQ',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor('#1E1B4B')
)

code_style = ParagraphStyle(
    'CodeText',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=7,
    leading=9,
    textColor=colors.HexColor('#1F2937')
)

story = []

def make_box(content_flowables, bg_color='#F4F4F8', border_color='#D0D0E0', padding=6):
    t = Table([[content_flowables]], colWidths=[letter[0] - 72])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor(border_color)),
        ('TOPPADDING', (0,0), (-1,-1), padding),
        ('BOTTOMPADDING', (0,0), (-1,-1), padding),
        ('LEFTPADDING', (0,0), (-1,-1), padding),
        ('RIGHTPADDING', (0,0), (-1,-1), padding),
    ]))
    return t

# --- PAGE 1 ---
story.append(Paragraph("LangGraph Engineering & Architecture — Study Notes", title_style))
story.append(Paragraph("Cognitive Retention Edition · System Invariants · Failure Domains · Contrastive Pairs & Verification", subtitle_style))
story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#3B4AAB'), spaceBefore=2, spaceAfter=6))

# THE THREE ANCHORS
story.append(Paragraph("THE THREE ARCHITECTURAL ANCHORS", h1_style))
anchors_text = [
    Paragraph("<b>1. A graph is a deterministic state machine wrapping probabilistic node executions.</b> Control flow, routing, iteration boundaries, and quality gates must be pure Python arithmetic—never LLM vibes.", body_style),
    Spacer(1, 2),
    Paragraph("<b>2. Parallel nodes write to channels, not shared variables.</b> Concurrent branches without an explicit reducer function will collide, overwrite data (last writer wins), or throw state exceptions.", body_style),
    Spacer(1, 2),
    Paragraph("<b>3. The graph computes state; the host handles the real world.</b> External side effects (Slack notifications, emails, database mutations, billing) live strictly in the caller/harness, never inside graph nodes.", body_style)
]
story.append(make_box(anchors_text, bg_color='#EEEDFE', border_color='#AFA9EC', padding=6))
story.append(Spacer(1, 6))

# THE DECODE ROUTINE
story.append(Paragraph("THE 6-QUESTION PRE-FLIGHT DECODE ROUTINE", h1_style))
routine_text = Paragraph(
    "<b>Before drawing any node or edge in code, answer these six questions:</b><br/>"
    "<b>1. State Schema:</b> What keys exist, and which keys require reducers to support parallel updates?<br/>"
    "<b>2. Probabilistic vs. Deterministic:</b> Which nodes generate stochastic content vs. enforce mathematical policy?<br/>"
    "<b>3. Topology:</b> Is the flow static linear, dynamic fan-out (<code>Send</code> API), or barrier synchronization (fan-in)?<br/>"
    "<b>4. Failure Modes:</b> Where can this fail? (Iteration limits, hallucinated schema, API timeouts, malformed keys).<br/>"
    "<b>5. Pause Boundaries:</b> Where does execution pause for human intervention (<code>interrupt()</code>) before committing state?<br/>"
    "<b>6. Side-Effect Boundary:</b> What state flags signal the external harness to trigger downstream real-world actions?",
    body_style
)
story.append(make_box([routine_text], bg_color='#F8F9FA', border_color='#E2E8F0', padding=6))
story.append(Spacer(1, 6))

# FAILURE DOMAIN 1: STATE & REDUCERS
story.append(Paragraph("FAILURE DOMAIN 1: STATE, REDUCERS & CONCURRENT CHANNELS", h1_style))
story.append(make_box([
    Paragraph("<b>Active Recall Q:</b> How does LangGraph prevent parallel nodes from overwriting each other when writing to the same state dictionary key?", q_style)
], bg_color='#F1F5F9', border_color='#CBD5E1', padding=5))
story.append(Spacer(1, 4))

story.append(Paragraph("<b>The Mechanism:</b> LangGraph state keys are <i>State Channels</i>. By default, returning a key overwrites it. When multiple nodes execute concurrently (via <code>Send()</code>), they emit updates simultaneously. Wrapping a type in <code>Annotated[Type, reducer_func]</code> instructs the runtime engine how to merge concurrent outputs instead of overwriting.", body_style))
story.append(Spacer(1, 4))

broken_state_code = """# BROKEN: Last-writer-wins race condition
class BrokenState(TypedDict):
    evaluations_raw: Dict[str, Any]
    # Node B silently overwrites Node A!"""

fixed_state_code = """# INVARIANT: Custom reducer merges dicts
def merge_evaluations(left: dict, right: dict) -> dict:
    if not left: left = {}
    if not right: right = {}
    return {**left, **right}

class ReportState(TypedDict):
    evaluations_raw: Annotated[dict, merge_evaluations]
    critique: Annotated[List[str], operator.add]"""

pair_table = Table([
    [
        Paragraph("<b>THE BROKEN PATTERN (Race Condition)</b><br/>"
                  "<i>Failure:</i> Silent overwrite. Last node to finish wins; other dimension scores vanish.", body_style),
        Paragraph("<b>THE INVARIANT (Channel Reducer)</b><br/>"
                  "<i>Mechanism:</i> Every parallel node's emitted dictionary is merged deterministically.", body_style)
    ],
    [
        Paragraph(f"<pre>{broken_state_code}</pre>", code_style),
        Paragraph(f"<pre>{fixed_state_code}</pre>", code_style)
    ]
], colWidths=[(letter[0]-72)/2, (letter[0]-72)/2])
pair_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#FFF5F5')),
    ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#F0FDF4')),
    ('BOX', (0,0), (0,-1), 0.75, colors.HexColor('#FEB2B2')),
    ('BOX', (1,0), (1,-1), 0.75, colors.HexColor('#86EFAC')),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4),
    ('RIGHTPADDING', (0,0), (-1,-1), 4),
]))
story.append(pair_table)
story.append(Spacer(1, 5))

story.append(Paragraph("Dynamic Fan-Out (<code>Send</code> API) & Barrier Synchronization", h2_style))
story.append(Paragraph(
    "<b>Problem:</b> Monolithic prompts evaluating multiple dimensions suffer from context dilution, prompt laziness, and sequential latency.<br/>"
    "<b>Solution:</b> Map-Reduce with <code>Send()</code>. The dispatcher dynamically returns a list of <code>Send('node_name', payload)</code> objects. LangGraph instantiates all target nodes in parallel. Routing all parallel nodes into an <code>aggregate</code> node creates an automatic <b>barrier synchronization gate</b>—LangGraph halts the aggregator until all concurrent evaluators resolve and write to the reducer channel.",
    body_style
))

story.append(PageBreak())

# --- PAGE 2 ---
story.append(Paragraph("FAILURE DOMAIN 2: CONTROL FLOW & DETERMINISTIC ROUTING", h1_style))
story.append(make_box([
    Paragraph("<b>Active Recall Q:</b> Why must Task Completion be evaluated as a Hard Gate before checking numeric score bands in router logic?", q_style)
], bg_color='#F1F5F9', border_color='#CBD5E1', padding=5))
story.append(Spacer(1, 4))

story.append(Paragraph("<b>The Order-of-Operations Router Trap:</b> Coupling the pass/fail boolean check directly with score thresholds caused drafts with a medium score (0.60) to fail the task gate prematurely and route to <code>revise</code>, completely bypassing the 0.50–0.75 Human Approval gate.", body_style))
story.append(Spacer(1, 4))

router_code = """def router(state: ReportState) -> str:
    # 1. HUMAN DECISION OVERRIDE (Highest priority)
    if state.get("human_decision") == "approve":
        return "end"
    elif state.get("human_decision") == "reject":
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"

    # 2. HARD TASK COMPLETION GATE (Did it fulfill fundamental requirements?)
    task_passed = state["evaluation"]["task_completion"]["passed"]
    if not task_passed:
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"

    # 3. DETERMINISTIC CONFIDENCE THRESHOLD BANDS
    score = score_evaluation(state["evaluation"])["score"]
    if score >= 0.75:
        return "end"        # High confidence (>= 0.75) -> Auto-approve
    elif score >= 0.50:
        return "approval"   # Medium confidence (0.50 to 0.75) -> Human Approval Gate
    else:
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"
"""
story.append(make_box([Paragraph(f"<pre>{router_code}</pre>", code_style)], bg_color='#FAFAFA', border_color='#E5E7EB', padding=5))
story.append(Spacer(1, 8))

# FAILURE DOMAIN 3: PERSISTENCE, INTERRUPTS & TIME TRAVEL
story.append(Paragraph("FAILURE DOMAIN 3: PERSISTENCE, INTERRUPTS & TIME TRAVEL", h1_style))
story.append(make_box([
    Paragraph("<b>Active Recall Q:</b> What happens to a thread's timeline if you call <code>update_state()</code> to fix a historical step but omit the <code>checkpoint_id</code>?", q_style)
], bg_color='#F1F5F9', border_color='#CBD5E1', padding=5))
story.append(Spacer(1, 4))

story.append(Paragraph(
    "<b>The Checkpointer Mechanism:</b> A checkpointer (<code>SqliteSaver</code>) writes an immutable snapshot after every node execution, forming a Directed Acyclic Graph (DAG) of states. Each snapshot contains <code>values</code> (state payload), <code>next</code> (nodes queued to run), <code>checkpoint_id</code>, and <code>parent_checkpoint_id</code>.<br/>"
    "<b>The Silent Rollback Trap:</b> If you omit <code>checkpoint_id</code> when calling <code>update_state(config, updates)</code>, LangGraph mutates the <b>HEAD (latest snapshot)</b> of the thread rather than rolling back to the past step. The operation succeeds silently without error, but the historical bug remains unfixed and your current state is corrupted.",
    body_style
))
story.append(Spacer(1, 4))

tt_table = Table([
    [
        Paragraph("<b>Operation</b>", bold_body_style),
        Paragraph("<b>LangGraph Command</b>", bold_body_style),
        Paragraph("<b>Timeline Effect</b>", bold_body_style)
    ],
    [
        Paragraph("<b>Inspect Past</b>", body_style),
        Paragraph("<code>graph.get_state_history(config)</code>", code_style),
        Paragraph("Read-only traversal of the thread's commit history (like <code>git log</code>).", body_style)
    ],
    [
        Paragraph("<b>Fork Timeline</b>", body_style),
        Paragraph("<code>graph.update_state(config_with_id, data)</code>", code_style),
        Paragraph("Creates a new branch from that historical point without deleting future steps.", body_style)
    ],
    [
        Paragraph("<b>Resume Branch</b>", body_style),
        Paragraph("<code>graph.invoke(None, config_with_id)</code>", code_style),
        Paragraph("Replays execution along the alternate reality branch from that exact state.", body_style)
    ]
], colWidths=[80, 180, letter[0] - 72 - 260])
tt_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4),
    ('RIGHTPADDING', (0,0), (-1,-1), 4),
]))
story.append(tt_table)

story.append(PageBreak())

# --- PAGE 3 ---
# FAILURE DOMAIN 4: HOST-GRAPH DECOUPLING
story.append(Paragraph("FAILURE DOMAIN 4: HOST–GRAPH DECOUPLING & SIDE EFFECTS", h1_style))
story.append(make_box([
    Paragraph("<b>Active Recall Q:</b> Why must external API calls (e.g. sending Slack/Email alerts on failure) never live inside a graph node?", q_style)
], bg_color='#F1F5F9', border_color='#CBD5E1', padding=5))
story.append(Spacer(1, 4))

story.append(Paragraph(
    "<b>The Rule:</b> Graph nodes must perform state computation only. External side effects (Slack, Twilio, Stripe, Email) must live in the host harness.<br/>"
    "<b>The Observable Failure:</b> If <code>failed_node</code> contains a live API call to send an email, running test suites, replaying historical checkpoints, or running time-travel forks will trigger real-world emails repeatedly.<br/>"
    "<b>The Invariant:</b> The node sets <code>needs_human_notification = True</code> in state. The host caller inspects the final state returned by <code>graph.invoke()</code> and handles external side effects safely.",
    body_style
))
story.append(Spacer(1, 6))

# TACTICAL TRAPS
story.append(Paragraph("TACTICAL ENGINEERING & ENVIRONMENT TRAPS", h1_style))
traps_text = Paragraph(
    "<b>1. Windows PowerShell venv Path Trap:</b> Running <code>pip install package</code> often invokes the global Windows user-site installer (e.g. Python 3.14) rather than the active virtual environment (Python 3.12). Always use <code>python -m pip install package</code> to target the active venv explicitly.<br/>"
    "<b>2. Dynamic Sub-Agent Dispatching:</b> <code>Send()</code> is not restricted to static functions. A Supervisor LLM can parse a user prompt and generate an arbitrary list of tasks at runtime, returning <code>[Send('coder_agent', task_a), Send('researcher_agent', task_b)]</code> to dynamically spawn multi-agent swarms.",
    body_style
)
story.append(make_box([traps_text], bg_color='#FFFBEB', border_color='#FDE68A', padding=6))
story.append(Spacer(1, 6))

# THE 60-SECOND RAPID-FIRE DRILL
story.append(Paragraph("THE 60-SECOND RAPID-FIRE VERIFICATION DRILL", h1_style))
drill_table = Table([
    [
        Paragraph("<b>Prompt / Distinction</b>", bold_body_style),
        Paragraph("<b>Exact Technical Answer</b>", bold_body_style)
    ],
    [
        Paragraph("<code>Send()</code> vs. Normal Edge", body_style),
        Paragraph("An edge transitions to a fixed node. <code>Send()</code> dynamically instantiates target nodes with specific payloads for parallel Map-Reduce execution.", body_style)
    ],
    [
        Paragraph("<code>MemorySaver</code> vs. <code>SqliteSaver</code>", body_style),
        Paragraph("<code>MemorySaver</code> is volatile in-RAM storage for fast unit tests. <code>SqliteSaver</code> is durable disk storage that survives application crashes and restarts.", body_style)
    ],
    [
        Paragraph("<code>StateSnapshot.values</code> vs. <code>.next</code>", body_style),
        Paragraph("<code>values</code> is the full state dictionary at that checkpoint. <code>next</code> is the tuple of node names scheduled to execute next.", body_style)
    ],
    [
        Paragraph("Silent State Trap", body_style),
        Paragraph("Calling <code>update_state()</code> without <code>checkpoint_id</code> mutates HEAD instead of historical state. Runs silently without error but corrupts current timeline.", body_style)
    ]
], colWidths=[140, letter[0] - 72 - 140])
drill_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ('TOPPADDING', (0,0), (-1,-1), 4),
    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ('LEFTPADDING', (0,0), (-1,-1), 4),
    ('RIGHTPADDING', (0,0), (-1,-1), 4),
]))
story.append(drill_table)

doc.build(story, canvasmaker=NumberedCanvas)
print("PDF generated successfully:", os.path.abspath(pdf_filename))