import sys
from playwright.sync_api import sync_playwright, Page
import time
import json
import os
from eu_ai_compliance_scraper import config
from eu_ai_compliance_scraper.utils.file_ops import save_json

def extract_visible_questions(page: Page):
    fields = page.query_selector_all('.wsf-field-wrapper')
    visible_fields = []
    for field in fields:
        try:
            if not field.is_visible():
                continue
        except Exception:
            continue
        options = field.query_selector_all('input[type="radio"], input[type="checkbox"]')
        if options:
            visible_fields.append(field)
    return visible_fields

def extract_question_and_options(field):
    h4 = field.query_selector('h4')
    p = field.query_selector('p')
    label = field.query_selector('label')
    question = ''
    if h4:
        question += h4.inner_text().strip() + ' '
    if p:
        question += p.inner_text().strip() + ' '
    if not question and label:
        question = label.inner_text().strip()
    question = question.strip()
    options = []
    for input_el in field.query_selector_all('input[type="radio"]'):
        value = input_el.get_attribute('value')
        if value:
            options.append({
                'type': 'radio',
                'value': value,
                'selector': input_el,
            })
    for input_el in field.query_selector_all('input[type="checkbox"]'):
        value = input_el.get_attribute('value')
        if value:
            options.append({
                'type': 'checkbox',
                'value': value,
                'selector': input_el,
            })
    return question, options

def is_end_of_form(page: Page):
    if page.query_selector('input[type="email"]'):
        return True
    if 'Your results' in page.content():
        return True
    return False

def replay_path(page: Page, url: str, path):
    """Reload the form and re-select all answers in the path."""
    page.goto(url)
    page.wait_for_selector('.wsf-field-wrapper', timeout=10000)
    time.sleep(1)
    for field_id, value in path:
        field = page.query_selector(f'#{field_id}')
        if not field:
            continue
        _, options = extract_question_and_options(field)
        for opt in options:
            if opt['value'] == value:
                if opt['type'] == 'radio':
                    opt['selector'].click()
                    time.sleep(0.2)
                elif opt['type'] == 'checkbox':
                    if not opt['selector'].is_checked():
                        opt['selector'].check()
                        time.sleep(0.2)
    return page

def walk_form(page: Page, url: str, path=None, seen_ids=None, depth=0):
    if path is None:
        path = []
    if seen_ids is None:
        seen_ids = set()
    if is_end_of_form(page):
        print(f"{'  '*depth}END OF FORM")
        return {'end': True}
    visible_fields = extract_visible_questions(page)
    # Find the first visible, unanswered field
    for field in visible_fields:
        field_id = field.get_attribute('id')
        if field_id in seen_ids:
            continue
        question, options = extract_question_and_options(field)
        if not question or not options:
            continue
        print(f"{'  '*depth}Q: {question}")
        node = {'question': question, 'options': []}
        for opt in options:
            print(f"{'  '*depth}  Option: {opt['value']}")
            # Click/select the option
            if opt['type'] == 'radio':
                opt['selector'].click()
                time.sleep(0.5)
                # Wait for a new field to appear
                new_field_id = None
                for _ in range(20):
                    new_fields = extract_visible_questions(page)
                    new_ids = {f.get_attribute('id') for f in new_fields}
                    diff = new_ids - seen_ids
                    if diff:
                        new_field_id = list(diff)[0]
                        break
                    time.sleep(0.2)
                new_path = path + [(field_id, opt['value'])]
                new_seen = seen_ids | {field_id}
                if new_field_id:
                    subtree = walk_form(page, url, new_path, new_seen, depth+1)
                else:
                    subtree = {'end': True}
                node['options'].append({
                    'value': opt['value'],
                    'next': subtree
                })
                # Replay path for next option
                page = replay_path(page, url, path)
            elif opt['type'] == 'checkbox':
                # For checkboxes, try single selection only for now
                opt['selector'].check()
                time.sleep(0.5)
                new_field_id = None
                for _ in range(20):
                    new_fields = extract_visible_questions(page)
                    new_ids = {f.get_attribute('id') for f in new_fields}
                    diff = new_ids - seen_ids
                    if diff:
                        new_field_id = list(diff)[0]
                        break
                    time.sleep(0.2)
                new_path = path + [(field_id, opt['value'])]
                new_seen = seen_ids | {field_id}
                if new_field_id:
                    subtree = walk_form(page, url, new_path, new_seen, depth+1)
                else:
                    subtree = {'end': True}
                node['options'].append({
                    'value': opt['value'],
                    'next': subtree
                })
                # Uncheck and replay path
                opt['selector'].uncheck()
                page = replay_path(page, url, path)
        return node
    if is_end_of_form(page):
        print(f"{'  '*depth}END OF FORM")
        return {'end': True}
    print(f"{'  '*depth}No more questions, but not at end marker.")
    return {'end': False}

def record_run(page: Page, url: str):
    """User-guided record mode: at each question, prompt user to select option(s)."""
    path = []
    seen_ids = set()
    while not is_end_of_form(page):
        visible_fields = extract_visible_questions(page)
        next_field = None
        for field in visible_fields:
            field_id = field.get_attribute('id')
            if field_id not in seen_ids:
                next_field = field
                break
        if not next_field:
            print("No more visible, unanswered questions.")
            break
        field_id = next_field.get_attribute('id')
        question, options = extract_question_and_options(next_field)
        print(f"\nQUESTION: {question}")
        for idx, opt in enumerate(options):
            print(f"  [{idx}] {opt['value']}")
        if options and options[0]['type'] == 'checkbox':
            print("Type comma-separated indices for all that apply (e.g., 0,2,3), or just one index:")
            user_input = input('Your selection: ').strip()
            indices = [int(i) for i in user_input.split(',') if i.strip().isdigit()]
            selected_values = []
            for i in indices:
                if 0 <= i < len(options):
                    options[i]['selector'].check()
                    selected_values.append(options[i]['value'])
            path.append((field_id, selected_values))
        else:
            print("Type the index of your selection:")
            user_input = input('Your selection: ').strip()
            try:
                idx = int(user_input)
                if 0 <= idx < len(options):
                    options[idx]['selector'].click()
                    path.append((field_id, options[idx]['value']))
                else:
                    print("Invalid index, skipping.")
            except Exception:
                print("Invalid input, skipping.")
        seen_ids.add(field_id)
        time.sleep(0.5)
    print("\nEND OF FORM. Saving run...")
    return path

def scrape_compliance_checker(url: str, record_mode=False) -> str:
    """
    If record_mode is True, prompt the user at each question to select options and record the run.
    Otherwise, run the automated logic.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('.wsf-field-wrapper', timeout=10000)
        time.sleep(1)
        if record_mode:
            run_path = record_run(page, url)
            # Save the run as a JSON path
            run_json_path = os.path.join(config.DATA_DIR, 'compliance_checker_recorded_run.json')
            save_json({'run': run_path}, run_json_path)
            print(f"Recorded run saved to {run_json_path}")
            html = page.content()
            browser.close()
            return html
        visible_fields = extract_visible_questions(page)
        if not visible_fields:
            print('No visible questions found on initial load.')
            print(page.content())
            browser.close()
            return ''
        first_field = None
        for field in visible_fields:
            question, options = extract_question_and_options(field)
            if any(opt['type'] == 'radio' for opt in options):
                first_field = field
                break
        if not first_field:
            print('No radio question found as first field.')
            print(page.content())
            browser.close()
            return ''
        question, options = extract_question_and_options(first_field)
        root = {'question': question, 'options': []}
        for opt in options:
            print(f"Top-level option: {opt['value']}")
            # Reload form for each top-level option
            page.goto(url)
            page.wait_for_selector('.wsf-field-wrapper', timeout=10000)
            time.sleep(1)
            visible_fields = extract_visible_questions(page)
            this_first_field = None
            for field in visible_fields:
                q, opts = extract_question_and_options(field)
                if any(o['type'] == 'radio' for o in opts):
                    this_first_field = field
                    break
            if not this_first_field:
                continue
            _, opts = extract_question_and_options(this_first_field)
            for o in opts:
                if o['value'] == opt['value']:
                    o['selector'].click()
                    time.sleep(0.5)
                    break
            answered_path = [(this_first_field.get_attribute('id'), opt['value'])]
            seen_ids = {this_first_field.get_attribute('id')}
            subtree = walk_form(page, url, answered_path, seen_ids, 1)
            root['options'].append({
                'value': opt['value'],
                'next': subtree
            })
        flow_json_path = os.path.join(config.DATA_DIR, 'compliance_checker_flow.json')
        save_json(root, flow_json_path)
        mermaid = generate_mermaid(root)
        mermaid_path = os.path.join(config.DATA_DIR, 'compliance_checker_flow.mmd')
        with open(mermaid_path, 'w', encoding='utf-8') as f:
            f.write(mermaid)
        print(f"Flow JSON saved to {flow_json_path}")
        print(f"Mermaid diagram saved to {mermaid_path}")
        html = page.content()
        browser.close()
        return html

def generate_mermaid(node, parent_id=None, node_id=[0], lines=None):
    if lines is None:
        lines = ["graph TD"]
    this_id = f"N{node_id[0]}"
    node_id[0] += 1
    label = node.get('question', 'End')
    label = label.replace('"', '\"')
    if parent_id:
        lines.append(f'  {parent_id}-->|""|{this_id}["{label}"]')
    else:
        lines.append(f'  {this_id}["{label}"]')
    for opt in node.get('options', []):
        opt_label = opt['value'].replace('"', '\"')
        next_id = node_id[0]
        generate_mermaid(opt['next'], this_id, node_id, lines)
    return '\n'.join(lines) 