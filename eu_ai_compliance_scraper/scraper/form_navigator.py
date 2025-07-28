import sys
import time
import os
from playwright.sync_api import sync_playwright, Page
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
        q_type = field.get_attribute('data-type')
        if q_type in ("radio", "checkbox"):
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
        input_id = input_el.get_attribute('id')
        if value and input_id:
            options.append({
                'type': 'radio',
                'value': value,
                'id': input_id,
            })
    for input_el in field.query_selector_all('input[type="checkbox"]'):
        value = input_el.get_attribute('value')
        input_id = input_el.get_attribute('id')
        if value and input_id:
            options.append({
                'type': 'checkbox',
                'value': value,
                'id': input_id,
            })
    return question, options

def is_end_of_form(page: Page):
    fields = page.query_selector_all('.wsf-field-wrapper')
    results_present = any(
        (f.get_attribute('data-type') == 'texteditor' and 'Your results' in (f.inner_text() or ""))
        for f in fields
    )
    incomplete_present = any(
        (f.get_attribute('data-type') == 'message' and 'Incomplete' in (f.inner_text() or ""))
        for f in fields
    )
    return results_present and not incomplete_present

def replay_path(page: Page, url: str, path):
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
                input_id = opt['id']
                input_el = page.query_selector(f'#{input_id}')
                if not input_el:
                    continue
                if opt['type'] == 'radio':
                    input_el.click()
                    time.sleep(0.2)
                elif opt['type'] == 'checkbox':
                    if not input_el.is_checked():
                        input_el.check()
                        time.sleep(0.2)
    return page

def walk_form(page: Page, url: str, path=None, seen_ids=None, depth=0):
    if path is None:
        path = []
    if seen_ids is None:
        seen_ids = set()

    if is_end_of_form(page):
        print(f"{'  '*depth}END OF FORM (complete)")
        return {'end': True}

    visible_fields = extract_visible_questions(page)
    actionable_fields = [f for f in visible_fields if f.get_attribute('id') not in seen_ids]

    if not actionable_fields:
        print(f"{'  '*depth}FORM INCOMPLETE -- More questions may be needed!")
        return {'incomplete': True}

    for field in actionable_fields:
        field_id = field.get_attribute('id')
        question, options = extract_question_and_options(field)
        if not question or not options:
            continue

        print(f"{'  '*depth}Q: {question}")
        node = {'id': field_id, 'question': question, 'options': []}

        for opt in options:
            print(f"{'  '*depth}  Option: {opt['value']}")
            input_id = opt['id']
            input_el = page.query_selector(f'#{input_id}')
            if not input_el:
                print(f"{'  '*depth}[WARN] Input {input_id} not found, skipping.")
                continue
            if opt['type'] == 'radio':
                input_el.click()
                time.sleep(0.8)
                new_path = path + [(field_id, opt['value'])]
                new_seen = seen_ids | {field_id}
                subtree = walk_form(page, url, new_path, new_seen, depth+1)
                node['options'].append({'value': opt['value'], 'next': subtree})
                page = replay_path(page, url, path)
            elif opt['type'] == 'checkbox':
                input_el.check()
                time.sleep(0.8)
                new_path = path + [(field_id, opt['value'])]
                new_seen = seen_ids | {field_id}
                subtree = walk_form(page, url, new_path, new_seen, depth+1)
                node['options'].append({'value': opt['value'], 'next': subtree})
                input_el.uncheck()
                page = replay_path(page, url, path)

        # Only one actionable field at a time, so return after exploring all options
        return node

    if not is_end_of_form(page):
        print(f"{'  '*depth}NO MORE QUESTIONS, FORM INCOMPLETE!")
        return {'incomplete': True}
    return {'end': True}

def record_run(page: Page, url: str):
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
                    input_id = options[i]['id']
                    input_el = page.query_selector(f'#{input_id}')
                    if input_el:
                        input_el.check()
                        selected_values.append(options[i]['value'])
            path.append((field_id, selected_values))
        else:
            print("Type the index of your selection:")
            user_input = input('Your selection: ').strip()
            try:
                idx = int(user_input)
                if 0 <= idx < len(options):
                    input_id = options[idx]['id']
                    input_el = page.query_selector(f'#{input_id}')
                    if input_el:
                        input_el.click()
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('.wsf-field-wrapper', timeout=10000)
        time.sleep(1)
        if record_mode:
            run_path = record_run(page, url)
            run_json_path = os.path.join(config.DATA_DIR, 'compliance_checker_recorded_run.json')
            save_json({'run': run_path}, run_json_path)
            print(f"Recorded run saved to {run_json_path}")
            html = page.content()
            browser.close()
            return html
        visible_fields = extract_visible_questions(page)
        first_field = None
        for field in visible_fields:
            question, options = extract_question_and_options(field)
            if any(opt['type'] == 'radio' for opt in options):
                first_field = field
                break
        if not first_field:
            print('No radio question found as first field.')
            browser.close()
            return ''
        question, options = extract_question_and_options(first_field)
        root = {'id': first_field.get_attribute('id'), 'question': question, 'options': []}
        for opt in options:
            print(f"Top-level option: {opt['value']}")
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
                    input_id = o['id']
                    input_el = page.query_selector(f'#{input_id}')
                    if input_el:
                        input_el.click()
                        time.sleep(0.8)
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
        print(f"Flow JSON saved to {flow_json_path}")
        # Optional Mermaid diagram
        try:
            mermaid = generate_mermaid(root)
            mermaid_path = os.path.join(config.DATA_DIR, 'compliance_checker_flow.mmd')
            with open(mermaid_path, 'w', encoding='utf-8') as f:
                f.write(mermaid)
            print(f"Mermaid diagram saved to {mermaid_path}")
        except Exception as e:
            print("Failed to generate Mermaid diagram:", e)
        html = page.content()
        browser.close()
        return html

def generate_mermaid(node, parent_id=None, node_id=[0], lines=None):
    if lines is None:
        lines = ["graph TD"]
    this_id = f"N{node_id[0]}"
    node_id[0] += 1
    label = node.get('question', 'End')
    label = label.replace('"', '\\"')
    if parent_id:
        lines.append(f'  {parent_id}-->|""|{this_id}["{label}"]')
    else:
        lines.append(f'  {this_id}["{label}"]')
    for opt in node.get('options', []):
        opt_label = opt['value'].replace('"', '\\"')
        generate_mermaid(opt['next'], this_id, node_id, lines)
    return '\n'.join(lines)
