const { getCookie } = require('./home_func'); 

describe ('home_func', () => {
    describe('getCookie', () => {
        test('should return the value of the specified cookie', () => {
            Object.defineProperty(document, 'cookie', {
                writable: true,
                value: 'Authorization=Bearer test-token; AnotherCookie=AnotherValue',
            });
    
            const result = getCookie('Authorization');
            expect(result).toBe('Bearer test-token');
        });
    
        test('should return undefined if the cookie is not found', () => {
            Object.defineProperty(document, 'cookie', {
                writable: true,
                value: 'AnotherCookie=AnotherValue'
            });
    
            const result = getCookie('Authorization');
            expect(result).toBeUndefined();
        });
    });

    describe('')
});
