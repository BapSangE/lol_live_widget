import { afterEach, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ScoreBar } from '../components/ScoreBar';
import { SettingsPanel } from '../components/SettingsPanel';
import { defaults } from '../lib/policies';
import { demoFrames } from '../lib/demo';
afterEach(cleanup);
it('keeps score visible and expands only on score button',()=>{
 const click=vi.fn();render(<ScoreBar state={demoFrames[0]} ticker={null} status="모의 데이터" onExpand={click}/>);
 expect(screen.getByText('2 : 1')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'경기 상세 열기'}));expect(click).toHaveBeenCalledOnce();
});
it('labels whole opacity and exposes keyboard-compatible stepped range',()=>{
 render(<SettingsPanel settings={defaults} matches={[]} onChange={()=>{}} onBack={()=>{}}/>);
 const range=screen.getByRole('slider',{name:/전체 불투명도/});expect(range).toHaveAttribute('min','10');expect(range).toHaveAttribute('max','100');expect(range).toHaveAttribute('step','5');expect(range).toHaveValue('65');
 expect(screen.getByRole('checkbox',{name:/호버/})).not.toBeChecked();expect(screen.getByRole('checkbox',{name:/자동 실행/})).not.toBeChecked();
});
