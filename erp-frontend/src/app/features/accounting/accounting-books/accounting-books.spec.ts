import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccountingBooks } from './accounting-books';

describe('AccountingBooks', () => {
  let component: AccountingBooks;
  let fixture: ComponentFixture<AccountingBooks>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccountingBooks]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AccountingBooks);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
