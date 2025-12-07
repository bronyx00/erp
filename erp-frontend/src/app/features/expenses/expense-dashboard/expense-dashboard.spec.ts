import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpenseDashboard } from './expense-dashboard';

describe('ExpenseDashboard', () => {
  let component: ExpenseDashboard;
  let fixture: ComponentFixture<ExpenseDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpenseDashboard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ExpenseDashboard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
