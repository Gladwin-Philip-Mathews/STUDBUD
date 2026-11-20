import { Component, computed, input } from '@angular/core';

/** A round badge with the person's initials; the colour comes from the name so it stays the same everywhere. */
@Component({
  selector: 'app-avatar',
  template: `<span class="avatar" aria-hidden="true" [style.background]="bg()" [style.color]="ink()" [style.width.rem]="size()" [style.height.rem]="size()" [style.font-size.rem]="size() * 0.4">{{ initials() }}</span>`,
  styles: `.avatar { display: inline-grid; place-items: center; border-radius: 50%; font-weight: 700; flex: none; user-select: none; }`,
})
export class Avatar {
  readonly name = input.required<string>();
  readonly size = input(2.25);
  private readonly hue = computed(() => [...this.name()].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7));
  readonly bg = computed(() => `hsl(${this.hue()} 80% 88%)`);
  readonly ink = computed(() => `hsl(${this.hue()} 60% 20%)`);
  readonly initials = computed(() => {
    const parts = this.name().trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '?') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
  });
}
