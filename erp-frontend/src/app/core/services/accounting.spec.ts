import { TestBed } from '@angular/core/testing';

import { Accounting } from './accounting';

describe('Accounting', () => {
  let service: Accounting;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Accounting);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
