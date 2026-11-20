import { Component, input, model } from '@angular/core';

export interface Section {
  id: string;
  label: string;
  count?: number | null;
}

/** A side list of section names with the chosen section's content beside it. Only one section shows at a time. */
@Component({
  selector: 'app-sections',
  template: `
    <div class="with-side">
      <nav class="side" [attr.aria-label]="label()">
        @for (s of sections(); track s.id) {
          <button type="button" class="side-item" [class.active]="s.id === active()" [attr.aria-current]="s.id === active() ? 'true' : null" (click)="active.set(s.id)">
            <span>{{ s.label }}</span>
            @if (s.count) { <span class="badge">{{ s.count }}</span> }
          </button>
        }
      </nav>
      <div class="panel"><ng-content /></div>
    </div>
  `,
  styles: `
    .with-side { display: grid; grid-template-columns: 13.5rem minmax(0, 1fr); gap: 1.5rem; align-items: start; }
    .side { position: sticky; top: 1rem; display: grid; gap: .25rem; background: var(--white); border: 1px solid var(--line); border-radius: var(--radius-lg); padding: .5rem; box-shadow: var(--shadow-sm); }
    .side-item { display: flex; justify-content: space-between; align-items: center; gap: .5rem; width: 100%; text-align: left; border: 0; border-radius: 10px; background: transparent; color: var(--ink); padding: .6rem .8rem; font-weight: 600; }
    .side-item:hover { background: var(--paper); color: var(--ink); }
    .side-item.active { background: var(--orange-tint); color: #000; box-shadow: inset 3px 0 0 var(--orange); }
    .panel { min-width: 0; }
    @media (max-width: 760px) {
      .with-side { grid-template-columns: 1fr; gap: 1rem; }
      .side { position: static; display: flex; overflow-x: auto; gap: .25rem; padding: .35rem; }
      .side-item { width: auto; white-space: nowrap; border-radius: 999px; }
      .side-item.active { box-shadow: none; }
    }
  `,
})
export class Sections {
  readonly sections = input.required<Section[]>();
  readonly active = model.required<string>();
  readonly label = input('Sections');
}
