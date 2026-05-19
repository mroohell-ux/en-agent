import LearningCard from './LearningCard';

export default function StackedLearningCards({ cards, onSubmit, activeIndex }: any) {
  return <div>{cards.map((c: any, i: number) => <LearningCard key={c.id} card={c} onSubmit={onSubmit} active={i===activeIndex} index={i} total={cards.length} />)}</div>;
}
