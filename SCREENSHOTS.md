# MCP Inspector Screenshots - Lab Requirements

This document guides you through capturing all required screenshots for the lab deliverables.

## Setup: Start MCP Inspector

Run this command in a terminal:

```bash
npx -y @modelcontextprotocol/inspector python -m implementation.mcp_server
```

This will open MCP Inspector at http://localhost:5173 (or similar port).

---

## 📸 Screenshot Checklist

### 1. **Server Connection** (screenshot: `01-server-discovery.png`)
**What to capture**: The MCP Inspector home/status page showing:
- Server connected successfully
- Server name: "SQLite Lab MCP Server"
- Status: Connected ✓

**Steps**:
1. MCP Inspector opens automatically
2. Take screenshot of the left sidebar or main panel
3. Save as: `img/01-server-discovery.png`

---

### 2. **Tools Discovery** (screenshot: `02-tools-list.png`)
**What to capture**: All 3 tools in the left sidebar:
- `search`
- `insert`
- `aggregate`

**Steps**:
1. In Inspector, look at the Tools section (left sidebar)
2. You should see 3 tools listed
3. Take screenshot showing all 3 tools
4. Save as: `img/02-tools-list.png`

---

### 3. **Search Tool Schema** (screenshot: `03-search-schema.png`)
**What to capture**: The `search` tool with its parameters:
- `table` (string)
- `filters` (optional, array of objects)
- `columns` (optional, array of strings)
- `limit` (integer, default 20)
- `offset` (integer, default 0)
- `order_by` (optional, string)
- `descending` (boolean, default false)

**Steps**:
1. Click on the `search` tool in the sidebar
2. The tool schema and description should appear
3. Take screenshot showing all parameters
4. Save as: `img/03-search-schema.png`

---

### 4. **Valid Search Call** (screenshot: `04-search-valid-call.png`)
**What to capture**: Successful search execution showing:
- Input parameters filled in
- Results returned with rows
- Metadata: `limit`, `offset`, `total`, `has_more`, `next_offset`

**Steps**:
1. Click `search` tool
2. Fill in parameters:
   - `table`: `students`
   - `filters`: `[{"column": "cohort", "op": "eq", "value": "A1"}]`
   - `limit`: `10`
3. Click "Call Tool"
4. Take screenshot of the results panel showing:
   - Rows array with student records
   - Pagination metadata
5. Save as: `img/04-search-valid-call.png`

---

### 5. **Invalid Search - Unknown Table** (screenshot: `05-search-invalid-table.png`)
**What to capture**: Error message when searching non-existent table:
- Error type: ValidationError
- Message: "unknown table: ..."

**Steps**:
1. Click `search` tool
2. Fill in:
   - `table`: `nonexistent_table`
   - `limit`: `10`
3. Click "Call Tool"
4. Take screenshot of the error message
5. Save as: `img/05-search-invalid-table.png`

---

### 6. **Insert Tool Schema** (screenshot: `06-insert-schema.png`)
**What to capture**: The `insert` tool parameters:
- `table` (string)
- `values` (object with column:value pairs)

**Steps**:
1. Click on the `insert` tool
2. Take screenshot showing the tool schema
3. Save as: `img/06-insert-schema.png`

---

### 7. **Valid Insert Call** (screenshot: `07-insert-valid-call.png`)
**What to capture**: Successful insert execution:
- Input values shown
- Returned object with `inserted` key
- Auto-generated `id`

**Steps**:
1. Click `insert` tool
2. Fill in:
   - `table`: `students`
   - `values`: 
     ```json
     {
       "name": "Test Student",
       "cohort": "A1",
       "score": 85.0
     }
     ```
3. Click "Call Tool"
4. Take screenshot of the result showing the inserted record with ID
5. Save as: `img/07-insert-valid-call.png`

---

### 8. **Aggregate Tool Schema** (screenshot: `08-aggregate-schema.png`)
**What to capture**: The `aggregate` tool parameters:
- `table` (string)
- `metric` (string: count, avg, sum, min, max)
- `column` (optional, string)
- `filters` (optional)
- `group_by` (optional, string)

**Steps**:
1. Click on the `aggregate` tool
2. Take screenshot showing all parameters
3. Save as: `img/08-aggregate-schema.png`

---

### 9. **Valid Aggregate Call** (screenshot: `09-aggregate-valid-call.png`)
**What to capture**: Successful aggregate execution:
- Metric: `avg` of `score`
- Grouped by: `cohort`
- Results showing group_key and value

**Steps**:
1. Click `aggregate` tool
2. Fill in:
   - `table`: `students`
   - `metric`: `avg`
   - `column`: `score`
   - `group_by`: `cohort`
3. Click "Call Tool"
4. Take screenshot of results showing:
   - group_key (A1, B2, etc.)
   - value (average scores)
5. Save as: `img/09-aggregate-valid-call.png`

---

### 10. **Resources Discovery** (screenshot: `10-resources-list.png`)
**What to capture**: All resources in the left sidebar:
- `schema://database`
- `schema://table/{table_name}` (resource template)

**Steps**:
1. Look at the Resources section in Inspector (left sidebar)
2. You should see 2 resources listed
3. Take screenshot showing both resources
4. Save as: `img/10-resources-list.png`

---

### 11. **Database Schema Resource** (screenshot: `11-schema-database.png`)
**What to capture**: Full database schema JSON:
- All 3 tables: students, courses, enrollments
- Each table's columns with types
- Complete JSON structure

**Steps**:
1. Click on `schema://database` resource
2. The full schema should display as formatted JSON
3. Take screenshot showing:
   - All tables listed
   - At least 2 table schemas visible (scroll if needed)
4. Save as: `img/11-schema-database.png`

---

### 12. **Table Schema Resource** (screenshot: `12-schema-table-students.png`)
**What to capture**: Per-table schema for `students`:
- Columns: id, name, cohort, score
- Column properties: name, type, notnull, default, pk

**Steps**:
1. Click on `schema://table/{table_name}`
2. Inspector might prompt for `table_name` parameter
3. Enter: `students`
4. Take screenshot showing the students table schema
5. Save as: `img/12-schema-table-students.png`

---

### 13. **Optional: Another Table Schema** (screenshot: `13-schema-table-courses.png`)
**What to capture**: Per-table schema for `courses`:
- Columns: id, code, title, duration

**Steps**:
1. Click on `schema://table/{table_name}` again
2. Enter: `courses`
3. Take screenshot showing the courses table schema
4. Save as: `img/13-schema-table-courses.png`

---

## 📋 Summary

| Screenshot | File | Content |
|-----------|------|---------|
| 1 | `01-server-discovery.png` | Server connected |
| 2 | `02-tools-list.png` | 3 tools discovered |
| 3 | `03-search-schema.png` | search tool schema |
| 4 | `04-search-valid-call.png` | Valid search result |
| 5 | `05-search-invalid-table.png` | Error handling |
| 6 | `06-insert-schema.png` | insert tool schema |
| 7 | `07-insert-valid-call.png` | Valid insert result |
| 8 | `08-aggregate-schema.png` | aggregate tool schema |
| 9 | `09-aggregate-valid-call.png` | Valid aggregate result |
| 10 | `10-resources-list.png` | 2 resources discovered |
| 11 | `11-schema-database.png` | Full database schema |
| 12 | `12-schema-table-students.png` | students table schema |
| 13 | `13-schema-table-courses.png` | courses table schema (optional) |

---

## 🎯 Tips for Great Screenshots

1. **Zoom Level**: Use 100% zoom for clarity
2. **Dark Mode**: If using dark theme, make sure text is readable
3. **Scroll to Show**: For long responses, take multiple screenshots or scroll to show key info
4. **Naming**: Use consistent naming: `NN-descriptive-name.png` (e.g., `04-search-valid-call.png`)
5. **Path**: Save all to `img/` directory

---

## ✅ Minimal Requirements (For Lab Grading)

If short on time, minimum screenshots needed:
1. ✅ `02-tools-list.png` - Proves tools are discoverable
2. ✅ `04-search-valid-call.png` - Proves search works
3. ✅ `07-insert-valid-call.png` - Proves insert works
4. ✅ `09-aggregate-valid-call.png` - Proves aggregate works
5. ✅ `10-resources-list.png` - Proves resources exist
6. ✅ `11-schema-database.png` - Proves schema resource works
7. ✅ `05-search-invalid-table.png` - Proves error handling

**Minimum: 7 screenshots** → Shows all required features

**Full: 13 screenshots** → Professional documentation

---

## Commands Reference

**Start Inspector:**
```bash
npx -y @modelcontextprotocol/inspector python -m implementation.mcp_server
```

**Start Verify (if screenshots offline):**
```bash
python -m implementation.verify_server
```

**Run Tests:**
```bash
pytest -v implementation/tests/test_db.py
```

---

Done! Follow the checklist above and you'll have all the screenshots needed for the lab deliverables. 📸
