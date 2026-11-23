"""Case analysis page: six AI tools on one matter (a LawVault case, or facts typed / uploaded here)."""
import datetime as dt
import streamlit as st
import ai, cases, config, docutil, jobs, legal, subscription, ui

BACKGROUND_NOTE = "This keeps running if you switch pages. You'll get a notification when it's done."
_KIND_LABEL = {"fact": "Fact", "legal": "Legal act", "deadline": "Deadline"}
_LEVEL_PILL = {"high": "red", "medium": "amber", "low": "green"}


# ---------- background-job plumbing ----------
def _snapshot(uid: str, scope: str):
    out = []
    for k in [*legal.TOOLS, "all"]:
        j = jobs.get(uid, "legal", f"{scope}:{k}")
        if j:
            out.append((k, j["running"], len(j["meta"].get("progress", {}).get("done", []))))
    return tuple(out)


def _poll(uid: str, scope: str):
    """While anything runs for this matter, redraw as soon as a step finishes."""
    before = _snapshot(uid, scope)
    if not any(running for _, running, _ in before):
        return

    @st.fragment(run_every=1.5)
    def _check():
        if _snapshot(uid, scope) != before:
            st.rerun(scope="app")
    _check()


# ---------- renderers ----------
def _fmt_date(e: dict) -> str:
    d = e["date"]
    try:
        if len(d) == 10:
            return f"{dt.date.fromisoformat(d):%d %b %Y}"
        if len(d) == 7:
            return f"{dt.date.fromisoformat(d + '-01'):%b %Y}"
    except ValueError:
        pass
    return d or e["date_text"] or "Undated"


def _render_timeline(u, ctx, text: str, work_id: str):
    tl = legal.parse_timeline(text)
    if not tl:
        st.markdown(text)
        return
    counts = {k: sum(1 for e in tl["events"] if e["kind"] == k) for k in _KIND_LABEL}
    st.caption(f"{len(tl['events'])} events  ·  {counts['legal']} legal acts  ·  {counts['deadline']} deadlines  ·  "
               "grey = fact, gold = legal act, red = deadline")
    items = []
    for e in tl["events"]:
        sig = f'<div class="lv-tl-sig">{ui.esc(e["significance"])}</div>' if e["significance"] else ""
        src = f'<div class="lv-tl-src">Source: {ui.esc(e["source"])}</div>' if e["source"] else ""
        items.append(f'<div class="lv-tl-item {e["kind"]}"><div class="lv-tl-date">{ui.esc(_fmt_date(e))}  ·  '
                     f'{_KIND_LABEL[e["kind"]]}</div><div class="lv-tl-ev">{ui.esc(e["event"])}</div>{sig}{src}</div>')
    ui.html_block('<div class="lv-tl">' + "".join(items) + "</div>")
    if tl["gaps"]:
        st.warning("**Gaps in the chronology**\n\n" + "\n".join(f"- {g}" for g in tl["gaps"]),
                   icon=":material/help:")
    upcoming = legal.future_deadlines(tl)
    if upcoming and ctx["case_id"] and ctx["editor"]:
        with st.expander(f"Add {len(upcoming)} upcoming date(s) to the case deadlines", icon=":material/event:"):
            picks = [i for i, f in enumerate(upcoming)
                     if st.checkbox(f"{f['date']:%a %d %b %Y} — {f['title']}", value=True, key=f"tlc_{work_id}_{i}")]
            if st.button("Add selected to case deadlines", key=f"tla_{work_id}", type="primary"):
                for i in picks:
                    due = dt.datetime.combine(upcoming[i]["date"], dt.time(9, 0)).timestamp()
                    cases.add_task(u["id"], ctx["case_id"], "deadline", upcoming[i]["title"], due)
                st.success(f"Added {len(picks)} deadline(s). They also appear on the team's calendars.")


def _matrix(risks) -> str:
    sev_rows, lik_cols = ("high", "medium", "low"), ("low", "medium", "high")
    score = {"high": 3, "medium": 2, "low": 1}
    shade = {1: "rgba(48,209,88,.14)", 2: "rgba(48,209,88,.14)", 3: "rgba(255,159,10,.16)",
             4: "rgba(255,159,10,.2)", 6: "rgba(255,69,58,.2)", 9: "rgba(255,69,58,.3)"}
    cells = ['<div></div>'] + [f"<div>Likelihood<br><b>{c.title()}</b></div>" for c in lik_cols]
    for s in sev_rows:
        cells.append(f"<div>Severity<br><b>{s.title()}</b></div>")
        for c in lik_cols:
            n = sum(1 for r in risks if r["severity"] == s and r["likelihood"] == c)
            cells.append(f'<div class="cell" style="background:{shade[score[s] * score[c]]}">{n or ""}</div>')
    return '<div class="lv-matrix">' + "".join(cells) + "</div>"


def _render_risks(text: str):
    rk = legal.parse_risks(text)
    if not rk:
        st.markdown(text)
        return
    a, b = st.columns([3, 2])
    with a:
        ui.html_block(f'<div class="lv-card"><div class="lv-stat-label">Overall exposure</div>'
                      f'<div class="lv-stat-value"><span class="lv-pill {_LEVEL_PILL[rk["overall"]]}" '
                      f'style="font-size:1rem;padding:.2rem .8rem">{rk["overall"].upper()}</span></div>'
                      f'<div class="lv-row-d" style="margin-top:.6rem">{ui.esc(rk["summary"])}</div></div>')
    with b:
        ui.html_block(_matrix(rk["risks"]))
    st.write("")
    for i, r in enumerate(rk["risks"], 1):
        ui.html_block(f"""<div class="lv-risk {r['severity']}"><div class="lv-risk-h">
            <span class="lv-risk-t">{i}. {ui.esc(r['title'])}</span>
            <span class="lv-pill grey">{ui.esc(r['area'] or 'general')}</span>
            <span class="lv-pill {_LEVEL_PILL[r['severity']]}">Severity: {r['severity']}</span>
            <span class="lv-pill {_LEVEL_PILL[r['likelihood']]}">Likelihood: {r['likelihood']}</span></div>
            <div class="lv-risk-d">{ui.esc(r['description'])}</div>
            {f'<div class="lv-risk-m"><b>Basis:</b> {ui.esc(r["basis"])}</div>' if r['basis'] else ''}
            {f'<div class="lv-risk-m"><b>Mitigation:</b> {ui.esc(r["mitigation"])}</div>' if r['mitigation'] else ''}
            </div>""")


# ---------- one tool ----------
def _tool_tab(u, ctx, tool: str, results: dict, all_running: bool):
    meta = legal.TOOLS[tool]
    scope = ctx["scope"]
    st.caption(f"**{meta['local']}** — {meta['blurb']}")
    job = jobs.get(u["id"], "legal", f"{scope}:{tool}")
    running = bool(job and job["running"])
    draft_type, instructions = "", ""
    if tool == "drafting":
        c1, c2 = st.columns([2, 3])
        draft_type = c1.selectbox("Document", legal.DRAFT_TYPES, key=f"dt_{scope}")
        instructions = c2.text_input("Instructions (optional)", key=f"di_{scope}",
                                     placeholder="e.g. demand payment within 7 days; firm but courteous tone")
    can_run = ctx["ready"] and ctx["editor"]
    label = "Run again" if tool in results else "Run"
    if tool == "drafting":
        label = "Draft it" if tool not in results else "Draft again"
    if st.button(label, key=f"run_{scope}_{tool}", icon=meta["icon"], type="secondary" if tool in results else "primary",
                 disabled=running or all_running or not can_run, help=ctx["why_not"] or None):
        prior = {k: v["text"] for k, v in results.items()}
        jobs.start(u["id"], "legal", f"{scope}:{tool}", legal.run, u, tool, ctx["case_id"], ctx["facts"],
                   ctx["jurisdiction"], ctx["language"], prior, draft_type, instructions,
                   label=meta["label"])
        st.rerun()
    if running:
        st.info(f"Working on the {meta['label'].lower()}… {BACKGROUND_NOTE}", icon=":material/hourglass_top:")
    elif job:
        if job["error"]:
            st.error(job["error"])
        jobs.pop(u["id"], "legal", f"{scope}:{tool}")

    res = results.get(tool)
    if not res:
        if not running:
            st.markdown(f'<div class="lv-empty">No {meta["label"].lower()} yet.</div>', unsafe_allow_html=True)
        return
    who = "you" if res["owner_id"] == u["id"] else res["author"].split("@")[0]
    st.caption(f"{res['title']}  ·  by {who}  ·  {dt.datetime.fromtimestamp(res['created_at']):%d %b %Y, %H:%M}")
    with st.container(border=True):
        if tool == "timeline":
            _render_timeline(u, ctx, res["text"], res["id"])
        elif tool == "risk":
            _render_risks(res["text"])
        else:
            st.markdown(res["text"])
    st.caption(ai.DISCLAIMER)
    md = f"# {res['title']}\n\n{legal.as_markdown(tool, res['text'])}\n\n---\n_{ai.DISCLAIMER}_\n"
    c1, c2, _ = st.columns([1, 1, 3])
    c1.download_button("Download .md", md, file_name=f"{tool}-{dt.date.today():%Y%m%d}.md", mime="text/markdown",
                       key=f"dl_{res['id']}", icon=":material/download:", use_container_width=True)
    if (res["owner_id"] == u["id"] or ctx["role"] == "owner") and \
            c2.button("Delete", key=f"del_{res['id']}", icon=":material/delete:", use_container_width=True):
        legal.delete(u["id"], res["id"])
        st.rerun()


# ---------- page ----------
def _source(u):
    """Returns the matter context: where the material comes from and what this user may do with it."""
    my_cases = cases.list_cases(u["id"])
    modes = ["case", "own"] if my_cases else ["own"]
    mode = st.segmented_control("Material", modes, default=modes[0], key="la_mode", label_visibility="collapsed",
                                format_func={"case": "A LawVault case", "own": "Facts I type or upload"}.get) or modes[0]
    ctx = dict(case_id=None, role=None, editor=True, facts="", ready=False, why_not="")
    if mode == "case":
        ids = [c["id"] for c in my_cases]
        cur = st.session_state.get("case_id") if st.session_state.get("case_id") in ids else ids[0]
        names = {c["id"]: c["title"] for c in my_cases}
        cid = st.selectbox("Case", ids, index=ids.index(cur), format_func=names.get)
        st.session_state["case_id"] = cid
        case = cases.get_case(u["id"], cid)
        if not case:
            st.error("You no longer have access to this case.")
            st.stop()
        n_docs, n_msgs = len(cases.list_documents(u["id"], cid)), len(cases.get_messages(u["id"], cid, 500))
        n_tasks = len(cases.list_tasks(u["id"], cid))
        st.caption(f"Uses the case's team chat ({n_msgs} messages), documents ({n_docs}) and deadlines ({n_tasks}). "
                   "Results are shared with everyone on the case.")
        extra = st.text_area("Additional facts (optional)", key=f"la_extra_{cid}", height=90,
                             placeholder="Anything the AI should know that isn't in the case yet.")
        ctx.update(case_id=cid, role=case["role"], editor=case["role"] != "viewer", facts=extra, ready=True,
                   scope=cid)
        if not ctx["editor"]:
            ctx["why_not"] = "You have view-only access to this case, so you can read results but not run tools."
            st.caption("👁️ View-only: you can read the results below but not run new ones.")
    else:
        facts = st.text_area("Facts of the matter", key="la_facts", height=200,
                             placeholder="Who the parties are, what was agreed, what went wrong and when, what the "
                                         "client wants. Bahasa Indonesia or English.")
        up = st.file_uploader(f"Attach a document (PDF or TXT, up to {config.MAX_UPLOAD_MB} MB)", type=["pdf", "txt"],
                              key="la_upload")
        doc_text = ""
        if up:
            doc_text, err = docutil.extract_text(up.name, up.getvalue())
            if err:
                st.error(err)
                doc_text = ""
            else:
                st.caption(f"{up.name}: {len(doc_text):,} characters will be included.")
        full = facts.strip() + (f"\n\nATTACHED DOCUMENT ({up.name}):\n{doc_text}" if doc_text else "")
        ready = len(full.strip()) >= 40
        ctx.update(facts=full, ready=ready, scope=f"own-{legal.matter_key(full)}",
                   why_not="" if ready else "Describe the facts first (at least a few sentences).")
        st.caption("Results on typed facts are private to you and kept for these exact facts.")
    return ctx


def render():
    u = st.session_state["user"]
    ui.page_header("Case analysis", "Analyse a matter end to end: the issues, a timeline, the legal basis, the "
                   "risks, a first draft and a recommended strategy.", eyebrow="AI")
    used, cap = subscription.ai_used_today(u["id"]), subscription.limits(u)["daily_ai"]
    st.caption(f"{ai.DISCLAIMER}  ·  {used} / {cap} AI requests used today  ·  Personal data is masked before it "
               "leaves LawVault.")

    ctx = _source(u)
    c1, c2 = st.columns(2)
    ctx["jurisdiction"] = c1.selectbox("Jurisdiction", legal.JURISDICTIONS, key="la_juris")
    ctx["language"] = c2.selectbox("Output language", list(legal.LANGUAGES), format_func=legal.LANGUAGES.get,
                                   key="la_lang")

    scope = ctx["scope"]
    results = legal.latest(u["id"], ctx["case_id"], None if ctx["case_id"] else scope[len("own-"):])
    all_job = jobs.get(u["id"], "legal", f"{scope}:all")
    all_running = bool(all_job and all_job["running"])
    any_single = any((j := jobs.get(u["id"], "legal", f"{scope}:{t}")) and j["running"] for t in legal.TOOLS)

    # progress strip
    pills = []
    progress = all_job["meta"].get("progress", {}) if all_job else {}
    for k, m in legal.TOOLS.items():
        if all_running and progress.get("current") == k:
            cls, mark = "amber", "◌"
        elif k in results:
            cls, mark = "", "✓"
        else:
            cls, mark = "grey", "·"
        pills.append(f'<span class="lv-pill {cls}" style="margin:0 .35rem .35rem 0">{mark} {ui.esc(m["label"])}</span>')
    ui.html_block("<div>" + "".join(pills) + "</div>")

    n = len(legal.FULL_RUN)
    b1, b2 = st.columns([2, 5])
    if b1.button("Run full analysis", type="primary", icon=":material/bolt:", use_container_width=True,
                 disabled=all_running or any_single or not (ctx["ready"] and ctx["editor"]),
                 help=ctx["why_not"] or "Analysis → timeline → legal basis → risks → strategy, each building on "
                                        f"the last. Uses {n} AI requests. Drafting is run separately."):
        prog = {"done": [], "current": None}
        prior = {k: v["text"] for k, v in results.items() if k == "drafting"}
        jobs.start(u["id"], "legal", f"{scope}:all", legal.run_all, u, ctx["case_id"], ctx["facts"],
                   ctx["jurisdiction"], ctx["language"], prior, prog, label="Full case analysis",
                   meta={"progress": prog})
        st.rerun()
    if all_running:
        cur = progress.get("current")
        b2.info(f"Step {len(progress.get('done', [])) + 1} of {n}: "
                f"{legal.TOOLS[cur]['label'] if cur else 'starting'}… {BACKGROUND_NOTE}", icon=":material/hourglass_top:")
    elif all_job:
        done, err = all_job["value"] or [], all_job["error"]
        if err:
            b2.error(err)
        elif done:
            b2.success(f"Full analysis finished: {len(done)} of {n} steps.", icon=":material/task_alt:")
        jobs.pop(u["id"], "legal", f"{scope}:all")
    elif used + n > cap and ctx["editor"]:
        b2.caption(f"A full run needs {n} AI requests; you have {max(0, cap - used)} left today.")

    tabs = st.tabs([m["label"] for m in legal.TOOLS.values()])  # fixed labels keep the open tab across reruns
    for tab, tool in zip(tabs, legal.TOOLS):
        with tab:
            _tool_tab(u, ctx, tool, results, all_running)
    _poll(u["id"], scope)
