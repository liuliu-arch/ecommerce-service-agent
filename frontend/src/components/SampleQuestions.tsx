import type { DemoScenarioSet } from "../data/demoScenarios";

type SampleQuestionsProps = {
  scenarioSet: DemoScenarioSet;
  disabled?: boolean;
  onSelect: (question: string) => void;
};

export function SampleQuestions({ scenarioSet, disabled = false, onSelect }: SampleQuestionsProps) {
  return (
    <section className="panel samples-panel">
      <div className="panel-header">
        <span>{scenarioSet.title}</span>
        <small>{scenarioSet.description}</small>
      </div>
      <div className="sample-grid">
        {scenarioSet.scenarios.map((scenario, index) => (
          <button
            className="sample-card"
            key={`${scenario.question}-${scenario.capability}-${index}`}
            disabled={disabled}
            onClick={() => onSelect(scenario.question)}
            type="button"
          >
            <strong>{scenario.question}</strong>
            <small>{scenario.capability}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
