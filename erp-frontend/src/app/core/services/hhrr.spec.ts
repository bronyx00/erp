import { TestBed } from '@angular/core/testing';

import { HhrrService } from './hhrr';

describe('HhrrService', () => {
  let service: HhrrService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(HhrrService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
