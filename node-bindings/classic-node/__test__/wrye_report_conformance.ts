import {JsWryeBashParser} from "../index.js";

/** Project actual native parser fields and the complete formatted report string. */
export function observeWryeReport(fixture: Record<string, any>): Record<string, any> {
    const parser = new JsWryeBashParser(fixture.warnings);
    const issues = parser.parse(fixture.html);
    return {
        issues: issues.map(issue => ({
            section: issue.sectionTitle, plugins: issue.plugins,
            warning: issue.warningMessage ?? null, severity: issue.severity
        })),
        report: JsWryeBashParser.formatReport(issues)
    };
}
